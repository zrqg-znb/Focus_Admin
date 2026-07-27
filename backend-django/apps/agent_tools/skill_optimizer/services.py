from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime
from time import perf_counter

from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from core.user.user_model import User

from ..providers.models import AgentSkillProvider
from ..providers.services import chat_completion, get_provider_for_user, normalize_upstream_text
from .models import AgentSkill, AgentSkillIteration, AgentSkillRun, AgentSkillTrace

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
MAX_FILE_SIZE = 1024 * 1024
MAX_FILE_COUNT = 50
ALLOWED_TEXT_EXTENSIONS = {'.md', '.txt', '.json', '.yaml', '.yml', '.py', '.js', '.ts', '.html', '.css', '.xml', '.toml', '.cfg', '.ini', '.sh'}
TRACE_CONTENT_LIMIT = 12_000


def _display_name(user: User | None) -> str:
    return (user.name or user.username) if user else ''


def _trace_content(content: str) -> str:
    """限制调用记录大小，避免长 SKILL.md 无限放大任务数据。"""
    if len(content) <= TRACE_CONTENT_LIMIT:
        return content
    return f'{content[:TRACE_CONTENT_LIMIT]}\n\n[内容已截断，仅保留前 {TRACE_CONTENT_LIMIT} 个字符]'


def _trace_request(messages: list[dict]) -> str:
    """以可读形式记录发送给模型的消息，不包含请求头或 API Key。"""
    return _trace_content('\n\n'.join(f'[{item.get("role", "user")}]\n{item.get("content", "")}' for item in messages))


def _start_trace(run: AgentSkillRun | None, stage: str, round_number: int, messages: list[dict]) -> AgentSkillTrace | None:
    """在网络请求前写入运行中轨迹，使长调用也能被前端感知。"""
    if not run or not stage:
        return None
    return AgentSkillTrace.objects.create(
        run=run,
        round_number=round_number,
        stage=stage,
        request_content=_trace_request(messages),
        sys_creator=run.sys_creator,
        sys_modifier=run.sys_creator,
    )


def _finish_trace(trace: AgentSkillTrace | None, started_at: float, response_content: str = '', error_message: str = '') -> None:
    """写入模型调用结果与耗时，失败调用同样保留在活动流中。"""
    if not trace:
        return
    trace.status = 'failed' if error_message else 'completed'
    trace.response_content = _trace_content(response_content)
    trace.error_message = error_message[:2000]
    trace.duration_ms = round((perf_counter() - started_at) * 1000)
    trace.save(update_fields=['status', 'response_content', 'error_message', 'duration_ms', 'sys_update_datetime'])


def _update_trace_stream(trace: AgentSkillTrace | None, started_at: float, response_content: str) -> None:
    """节流更新运行中响应，让前端可在模型生成期间读取增量文本。"""
    if not trace:
        return
    trace.response_content = _trace_content(response_content)
    trace.duration_ms = round((perf_counter() - started_at) * 1000)
    trace.save(update_fields=['response_content', 'duration_ms', 'sys_update_datetime'])


def _chat_completion(provider: AgentSkillProvider, messages: list[dict], temperature: float = 0.2, *, run: AgentSkillRun | None = None, stage: str = '', round_number: int = 0) -> str:
    """为 Skill Optimizer 调用平台模型服务并持久化本次运行轨迹。"""
    trace = _start_trace(run, stage, round_number, messages)
    started_at = perf_counter()
    try:
        content = chat_completion(
            provider,
            messages,
            temperature,
            on_stream_update=(lambda response: _update_trace_stream(trace, started_at, response)) if trace else None,
        )
    except Exception as exc:
        _finish_trace(trace, started_at, error_message=str(exc))
        raise
    _finish_trace(trace, started_at, response_content=content)
    return content


def _safe_zip_entries(content: bytes) -> tuple[list[str], str, dict[str, bytes]]:
    """安全校验 ZIP，并提取可展示文本文件和必需的 SKILL.md。"""
    if len(content) > MAX_UPLOAD_SIZE:
        raise HttpError(413, '技能包不能超过 10MB')
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise HttpError(400, '上传文件不是有效 ZIP') from exc
    files, text_files = [], {}
    for info in archive.infolist():
        name = info.filename.replace('\\', '/')
        if info.is_dir() or name.startswith('__MACOSX/') or '/.DS_Store' in name or name.endswith('.DS_Store'):
            continue
        if name.startswith('/') or '..' in name.split('/'):
            raise HttpError(400, '技能包包含不安全路径')
        if len(files) >= MAX_FILE_COUNT:
            raise HttpError(413, '技能包文件数量不能超过 50 个')
        if info.file_size > MAX_FILE_SIZE:
            raise HttpError(413, f'文件 {name} 不能超过 1MB')
        files.append(name)
        if os.path.splitext(name)[1].lower() in ALLOWED_TEXT_EXTENSIONS:
            text_files[name] = archive.read(info).decode('utf-8', errors='replace')
    skill_path = next((item for item in files if item.rsplit('/', 1)[-1] == 'SKILL.md'), '')
    if not skill_path or skill_path not in text_files:
        raise HttpError(400, '技能包必须包含 UTF-8 文本格式的 SKILL.md')
    return files, skill_path, text_files


def upload_skill(user: User, filename: str, content: bytes) -> dict:
    """保存原始 ZIP 与技能提示词，不执行包内任何文件。"""
    files, skill_path, text_files = _safe_zip_entries(content)
    raw_skill_md = text_files[skill_path]
    name_match = re.search(r'^name:\s*["\']?([^\n"\']+)', raw_skill_md, re.MULTILINE)
    description_match = re.search(r'^description:\s*["\']?([^\n"\']+)', raw_skill_md, re.MULTILINE)
    skill = AgentSkill.objects.create(name=(name_match.group(1).strip() if name_match else os.path.splitext(filename)[0])[:160],
                                      description=(description_match.group(1).strip() if description_match else ''), original_filename=filename,
                                      archive_content=content, file_manifest=files, original_skill_md=raw_skill_md, latest_skill_md=raw_skill_md,
                                      sys_creator=user, sys_modifier=user)
    return _serialize_skill(skill)


def _serialize_skill(skill: AgentSkill) -> dict:
    return {'id': str(skill.id), 'name': skill.name, 'description': skill.description, 'original_filename': skill.original_filename,
            'file_manifest': skill.file_manifest, 'sys_creator_name': _display_name(skill.sys_creator), 'sys_create_datetime': skill.sys_create_datetime}


def list_skills(page: int, page_size: int, keyword: str = '') -> dict:
    """按关键词分页展示可优化技能包。"""
    queryset = AgentSkill.objects.filter(is_deleted=False).select_related('sys_creator')
    if keyword.strip():
        queryset = queryset.filter(name__icontains=keyword.strip())
    return {'items': [_serialize_skill(item) for item in queryset[(page - 1) * page_size: page * page_size]], 'total': queryset.count()}


def create_run(user: User, payload) -> dict:
    """为指定技能和模型档案创建待配置优化任务。"""
    skill = get_object_or_404(AgentSkill, id=payload.skill_id, is_deleted=False)
    provider = get_provider_for_user(user, payload.provider_id, active_only=True)
    run = AgentSkillRun.objects.create(skill=skill, provider=provider, provider_snapshot={'name': provider.name, 'base_url': provider.base_url, 'model': provider.model},
                                       max_rounds=payload.max_rounds, original_skill_md=skill.latest_skill_md or skill.original_skill_md,
                                       sys_creator=user, sys_modifier=user)
    return _serialize_run(run)


def _parse_json(text: str, fallback):
    """容忍模型附加说明，提取首段 JSON 数据。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return fallback


def _generate_config(run: AgentSkillRun) -> tuple[list[dict], list[dict]]:
    """从技能提示词生成可由用户复核的测试场景和二元标准。"""
    content = _chat_completion(run.provider, [{'role': 'system', 'content': 'You design evaluation plans for agent skills. Return JSON only.'},
        {'role': 'user', 'content': f'''Analyze this SKILL.md and return JSON: {{"scenarios":[{{"id":1,"name":"","input":""}}],"evaluations":[{{"id":1,"name":"","question":"binary yes/no question","pass_condition":""}}]}}. Generate 3-4 scenarios and 4-6 evaluations.\n\n{run.original_skill_md}'''}], run=run, stage='config_generation')
    payload = _parse_json(content, {})
    scenarios, evaluations = payload.get('scenarios', []), payload.get('evaluations', []) if isinstance(payload, dict) else ([], [])
    if not scenarios or not evaluations:
        raise RuntimeError('模型未返回有效的测试场景和评估标准')
    return scenarios, evaluations


def configure_run(user: User, run_id: str, payload, regenerate: bool = False) -> dict:
    """保存用户选择的场景和标准，或由模型重新生成默认配置。"""
    run = get_object_or_404(AgentSkillRun, id=run_id, is_deleted=False)
    if run.status not in ('draft', 'failed', 'cancelled'):
        raise HttpError(400, '运行中的任务不能修改配置')
    try:
        scenarios, evaluations = _generate_config(run) if regenerate else (payload.scenarios, payload.evaluations)
    except RuntimeError as exc:
        # 模型配置错误属于上游依赖失败，向页面返回可操作的信息而非未处理的 500。
        raise HttpError(502, f'生成评测配置失败：{exc}') from exc
    if not scenarios or not evaluations:
        raise HttpError(400, '至少需要一个测试场景和一个评估标准')
    run.scenarios, run.evaluations, run.status, run.error_message, run.sys_modifier = scenarios, evaluations, 'draft', '', user
    run.save()
    return _serialize_run(run)


def _serialize_run(run: AgentSkillRun) -> dict:
    return {'id': str(run.id), 'skill_id': str(run.skill_id), 'skill_name': run.skill.name, 'provider_id': str(run.provider_id),
            'provider_name': run.provider_snapshot.get('name', run.provider.name), 'provider_model': run.provider_snapshot.get('model', run.provider.model),
            'status': run.status, 'max_rounds': run.max_rounds, 'scenarios': run.scenarios, 'evaluations': run.evaluations,
            'baseline_score': run.baseline_score, 'final_score': run.final_score, 'original_skill_md': run.original_skill_md,
            'improved_skill_md': run.improved_skill_md, 'error_message': run.error_message, 'cancel_requested': run.cancel_requested,
            'started_at': run.started_at, 'completed_at': run.completed_at, 'sys_creator_name': _display_name(run.sys_creator), 'sys_create_datetime': run.sys_create_datetime}


def get_run(run_id: str) -> dict:
    """返回一次任务的最新状态和结果。"""
    return _serialize_run(get_object_or_404(AgentSkillRun.objects.select_related('skill', 'provider', 'sys_creator'), id=run_id, is_deleted=False))


def list_runs(page: int, page_size: int, status: str = '', provider_id: str = '') -> dict:
    """分页返回优化记录，支持状态和模型档案表头筛选。"""
    queryset = AgentSkillRun.objects.filter(is_deleted=False).select_related('skill', 'provider', 'sys_creator')
    if status: queryset = queryset.filter(status=status)
    if provider_id: queryset = queryset.filter(provider_id=provider_id)
    return {'items': [_serialize_run(item) for item in queryset[(page - 1) * page_size: page * page_size]], 'total': queryset.count()}


def start_run(user: User, run_id: str) -> dict:
    """提交具备配置的任务到独立 Celery 队列。"""
    from ..tasks import dispatch_agent_skill_run, run_agent_skill
    run = get_object_or_404(AgentSkillRun, id=run_id, is_deleted=False)
    if run.status not in ('draft', 'failed', 'cancelled') or not run.scenarios or not run.evaluations:
        raise HttpError(400, '请先完成场景和评估标准配置')
    run.status, run.cancel_requested, run.error_message, run.sys_modifier = 'queued', False, '', user
    run.save(update_fields=['status', 'cancel_requested', 'error_message', 'sys_modifier', 'sys_update_datetime'])
    error = dispatch_agent_skill_run(run_agent_skill, str(run.id))
    if error:
        run.status, run.error_message = 'failed', error
        run.save(update_fields=['status', 'error_message', 'sys_update_datetime'])
        raise HttpError(503, error)
    return _serialize_run(run)


def cancel_run(user: User, run_id: str) -> dict:
    """写入取消标记；Worker 会在轮次边界主动停止。"""
    run = get_object_or_404(AgentSkillRun, id=run_id, is_deleted=False)
    if run.status not in ('queued', 'running'):
        raise HttpError(400, '当前任务不能取消')
    run.cancel_requested, run.sys_modifier = True, user
    run.save(update_fields=['cancel_requested', 'sys_modifier', 'sys_update_datetime'])
    return _serialize_run(run)


def _score_skill(provider: AgentSkillProvider, skill_md: str, scenarios: list[dict], evaluations: list[dict], *, run: AgentSkillRun | None = None, round_number: int = 0, phase: str = 'baseline') -> tuple[float, list[dict]]:
    """模拟执行技能并以每个场景的二元标准计算百分制评分。"""
    results, passed, total = [], 0, 0
    for scenario in scenarios:
        output = _chat_completion(provider, [{'role': 'system', 'content': 'Follow the supplied skill exactly. Return only the response to the user.'},
            {'role': 'user', 'content': f'SKILL.md:\n{skill_md}\n\nUser request:\n{scenario.get("input", "")}'}], run=run, stage=f'{phase}_response', round_number=round_number)
        score_text = _chat_completion(provider, [{'role': 'system', 'content': 'Evaluate the response. Return JSON only.'},
            {'role': 'user', 'content': f'Input: {scenario.get("input", "")}\nOutput: {output}\nCriteria: {json.dumps(evaluations, ensure_ascii=False)}\nReturn {{"results":[{{"eval_id":1,"passed":true,"reason":""}}]}}'}], temperature=0, run=run, stage=f'{phase}_evaluation', round_number=round_number)
        scored = _parse_json(score_text, {}).get('results', [])
        for result in scored:
            is_passed = bool(result.get('passed'))
            results.append({**result, 'scenario_id': scenario.get('id')})
            passed += int(is_passed); total += 1
    return (round(passed / max(total, 1) * 100, 1), results)


def _diagnose_and_mutate(provider: AgentSkillProvider, skill_md: str, failures: list[dict], *, run: AgentSkillRun | None = None, round_number: int = 0) -> tuple[dict, dict]:
    """使用诊断与改写两个独立提示词得到一次受限的技能改动。"""
    analysis_text = _chat_completion(provider, [{'role': 'system', 'content': 'Diagnose skill failures. Return JSON only.'},
        {'role': 'user', 'content': f'Return {{"diagnosis":"","strategy":"add_example|add_constraint|restructure|add_edge_case","target":"","suggested_change":""}} for failures: {json.dumps(failures[:8], ensure_ascii=False)}'}], run=run, stage='diagnosis', round_number=round_number)
    analysis = _parse_json(analysis_text, {'diagnosis': 'Unable to diagnose', 'strategy': 'add_constraint', 'target': '', 'suggested_change': ''})
    mutation_text = _chat_completion(provider, [{'role': 'system', 'content': 'Edit a SKILL.md. Return JSON only; preserve YAML frontmatter and make exactly one targeted change.'},
        {'role': 'user', 'content': f'SKILL.md:\n{skill_md}\n\nDiagnosis:\n{json.dumps(analysis, ensure_ascii=False)}\nReturn {{"description":"","new_skill_md":""}}'}], run=run, stage='mutation', round_number=round_number)
    mutation = _parse_json(mutation_text, {'description': '未能解析模型改写结果', 'new_skill_md': skill_md})
    return analysis, mutation


def execute_run(run_id: str) -> None:
    """Celery Worker 入口：执行基线和最多 N 次可取消的优化迭代。"""
    run = AgentSkillRun.objects.select_related('skill', 'provider').get(id=run_id, is_deleted=False)
    run.status, run.started_at = 'running', timezone.now(); run.save(update_fields=['status', 'started_at', 'sys_update_datetime'])
    try:
        baseline_score, baseline_details = _score_skill(run.provider, run.original_skill_md, run.scenarios, run.evaluations, run=run, phase='baseline')
        AgentSkillIteration.objects.update_or_create(run=run, round_number=0, defaults={'status': 'baseline', 'score_before': baseline_score, 'score_after': baseline_score,
            'kept': True, 'evaluation_summary': baseline_details, 'sys_creator': run.sys_creator, 'sys_modifier': run.sys_creator})
        current_md, current_score, details = run.original_skill_md, baseline_score, baseline_details
        run.baseline_score = baseline_score; run.save(update_fields=['baseline_score', 'sys_update_datetime'])
        for round_number in range(1, run.max_rounds + 1):
            run.refresh_from_db(fields=['cancel_requested'])
            if run.cancel_requested:
                run.status, run.completed_at = 'cancelled', timezone.now(); run.save(update_fields=['status', 'completed_at', 'sys_update_datetime']); return
            failures = [item for item in details if not item.get('passed')]
            analysis, mutation = _diagnose_and_mutate(run.provider, current_md, failures, run=run, round_number=round_number)
            candidate_md = str(mutation.get('new_skill_md') or current_md)
            candidate_score, candidate_details = _score_skill(run.provider, candidate_md, run.scenarios, run.evaluations, run=run, round_number=round_number, phase='candidate')
            kept = candidate_score > current_score
            AgentSkillIteration.objects.update_or_create(run=run, round_number=round_number, defaults={'status': 'kept' if kept else 'discarded', 'score_before': current_score,
                'score_after': candidate_score, 'kept': kept, 'strategy': str(analysis.get('strategy', '')), 'diagnosis': str(analysis.get('diagnosis', '')),
                'description': str(mutation.get('description', '')), 'evaluation_summary': candidate_details, 'sys_creator': run.sys_creator, 'sys_modifier': run.sys_creator})
            if kept: current_md, current_score, details = candidate_md, candidate_score, candidate_details
        with transaction.atomic():
            run.final_score, run.improved_skill_md, run.status, run.completed_at = current_score, current_md, 'completed', timezone.now()
            run.save(update_fields=['final_score', 'improved_skill_md', 'status', 'completed_at', 'sys_update_datetime'])
            run.skill.latest_skill_md, run.skill.sys_modifier = current_md, run.sys_creator
            run.skill.save(update_fields=['latest_skill_md', 'sys_modifier', 'sys_update_datetime'])
    except Exception as exc:
        run.status, run.error_message, run.completed_at = 'failed', str(exc), timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at', 'sys_update_datetime'])


def list_iterations(run_id: str) -> list[dict]:
    """返回按轮次排序的评分与改写记录。"""
    return [{'id': str(item.id), 'round_number': item.round_number, 'status': item.status, 'score_before': item.score_before, 'score_after': item.score_after,
             'kept': item.kept, 'strategy': item.strategy, 'diagnosis': item.diagnosis, 'description': item.description,
             'evaluation_summary': item.evaluation_summary, 'sys_create_datetime': item.sys_create_datetime} for item in AgentSkillIteration.objects.filter(run_id=run_id, is_deleted=False)]


def list_traces(run_id: str) -> list[dict]:
    """按发生顺序返回调用轨迹，供工作台实时活动流轮询展示。"""
    return [
        {
            'id': str(item.id), 'round_number': item.round_number, 'stage': item.stage,
            'status': item.status,
            # 已持久化的旧轨迹也在读取时修复，无需要求用户重跑历史任务。
            'request_content': normalize_upstream_text(item.request_content),
            'response_content': normalize_upstream_text(item.response_content),
            'error_message': normalize_upstream_text(item.error_message),
            'duration_ms': item.duration_ms, 'sys_create_datetime': item.sys_create_datetime,
        }
        for item in AgentSkillTrace.objects.filter(run_id=run_id, is_deleted=False)
    ]


def download_run(run_id: str) -> FileResponse:
    """复用原 ZIP 的所有内容，仅替换根目录或嵌套目录内的 SKILL.md。"""
    run = get_object_or_404(AgentSkillRun.objects.select_related('skill'), id=run_id, is_deleted=False, status='completed')
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(bytes(run.skill.archive_content))) as source, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            content = source.read(info)
            if not info.is_dir() and info.filename.replace('\\', '/').rsplit('/', 1)[-1] == 'SKILL.md':
                content = run.improved_skill_md.encode('utf-8')
            target.writestr(info, content)
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename=f'{run.skill.name}-improved.zip', content_type='application/zip')
