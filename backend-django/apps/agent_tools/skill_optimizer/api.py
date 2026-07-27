from ninja import File, Query, Router
from ninja.files import UploadedFile

from common.fu_auth import BearerAuth as GlobalAuth

from . import services
from .schemas import (
    IterationOut,
    PageOut,
    RunConfigIn,
    RunCreateIn,
    RunOut,
    SkillOut,
    TraceOut,
)

router = Router(tags=['AgentTools-SkillOptimizer'], auth=GlobalAuth())


@router.get('/skills', response=PageOut, summary='技能包列表')
def list_skills(request, page: int = 1, pageSize: int = 20, keyword: str = ''):
    """分页返回已上传的 Skill Optimizer 技能包。"""
    return services.list_skills(max(page, 1), min(max(pageSize, 1), 100), keyword)


@router.post('/skills/upload', response=SkillOut, summary='上传技能包')
def upload_skill(request, file: UploadedFile = File(...)):
    """上传 ZIP 技能包并安全校验；服务端不会执行其中任何脚本。"""
    if not (file.name or '').lower().endswith('.zip'):
        from ninja.errors import HttpError
        raise HttpError(400, '只支持上传 ZIP 技能包')
    return services.upload_skill(request.auth, file.name or 'skill.zip', file.read())


@router.post('/runs', response=RunOut, summary='创建优化任务')
def create_run(request, payload: RunCreateIn):
    """基于指定技能包和模型档案创建待配置优化任务。"""
    return services.create_run(request.auth, payload)


@router.get('/runs', response=PageOut, summary='优化记录列表')
def list_runs(request, page: int = 1, pageSize: int = 20, status: str = '', provider_id: str = ''):
    """分页返回优化记录，支持状态和模型档案筛选。"""
    return services.list_runs(max(page, 1), min(max(pageSize, 1), 100), status, provider_id)


@router.get('/runs/{run_id}', response=RunOut, summary='优化任务详情')
def get_run(request, run_id: str):
    """读取运行中的进度或已完成任务的最终结果。"""
    return services.get_run(run_id)


@router.put('/runs/{run_id}/config', response=RunOut, summary='保存优化配置')
def configure_run(request, run_id: str, payload: RunConfigIn):
    """保存用户编辑后的测试场景与二元评估标准。"""
    return services.configure_run(request.auth, run_id, payload)


@router.post('/runs/{run_id}/config/regenerate', response=RunOut, summary='重新生成优化配置')
def regenerate_run_config(request, run_id: str):
    """调用已选模型重新生成场景和评估标准。"""
    return services.configure_run(request.auth, run_id, RunConfigIn(scenarios=[], evaluations=[]), regenerate=True)


@router.post('/runs/{run_id}/start', response=RunOut, summary='启动优化任务')
def start_run(request, run_id: str):
    """把优化任务投递到 Skill Optimizer 独立 Celery 队列。"""
    return services.start_run(request.auth, run_id)


@router.post('/runs/{run_id}/cancel', response=RunOut, summary='取消优化任务')
def cancel_run(request, run_id: str):
    """请求取消运行中的任务，Worker 会在轮次边界停止。"""
    return services.cancel_run(request.auth, run_id)


@router.get('/runs/{run_id}/iterations', response=list[IterationOut], summary='优化迭代记录')
def list_iterations(request, run_id: str):
    """读取基线和每轮单点改写的评分记录。"""
    return services.list_iterations(run_id)


@router.get('/runs/{run_id}/traces', response=list[TraceOut], summary='优化调用过程')
def list_traces(request, run_id: str):
    """返回任务中每次模型调用的请求、回复、耗时和失败信息。"""
    return services.list_traces(run_id)


@router.get('/runs/{run_id}/download', summary='下载改进技能包')
def download_run(request, run_id: str):
    """下载保留原文件、仅替换 SKILL.md 的改进 ZIP 包。"""
    return services.download_run(run_id)
