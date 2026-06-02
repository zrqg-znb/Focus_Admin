import os
import hashlib
import json
import logging
import base64
import binascii
from datetime import datetime
from typing import Any, Iterable
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from apps.code_scan.models import (
    ScanFinding,
    ScanProject,
    ScanResult,
    ScanResultDetail,
    ScanResultOccurrence,
    ScanTask,
    ShieldApplication,
)
from apps.code_scan.parsers.factory import ParserFactory
from core.user.user_model import User

logger = logging.getLogger(__name__)

class ScanService:
    @staticmethod
    def _soft_delete_queryset(queryset, modifier_id: str | None = None) -> int:
        update_kwargs = {
            "is_deleted": True,
            "sys_update_datetime": timezone.now(),
        }
        if modifier_id:
            update_kwargs["sys_modifier_id"] = modifier_id
        return queryset.filter(is_deleted=False).update(**update_kwargs)

    @staticmethod
    def _soft_delete_light_queryset(queryset) -> int:
        return queryset.filter(is_deleted=False).update(
            is_deleted=True,
            updated_at=timezone.now(),
        )

    @staticmethod
    def _normalize_path(value: str | None) -> str:
        return (value or "").strip().replace("\\", "/")

    @staticmethod
    def _normalize_path_prefixes(raw_value: Any) -> list[str]:
        if raw_value is None:
            return []

        values: Iterable[Any]
        if isinstance(raw_value, str):
            values = raw_value.replace(",", "\n").splitlines()
        elif isinstance(raw_value, (list, tuple, set)):
            values = raw_value
        else:
            return []

        prefixes: list[str] = []
        seen: set[str] = set()
        for item in values:
            prefix = ScanService._normalize_path(str(item))
            if not prefix or prefix in seen:
                continue
            seen.add(prefix)
            prefixes.append(prefix)
        return prefixes

    @staticmethod
    def _is_path_prefix_shielded(file_path: str, path_prefixes: list[str]) -> bool:
        normalized_path = ScanService._normalize_path(file_path)
        if not normalized_path or not path_prefixes:
            return False
        return any(normalized_path.startswith(prefix) for prefix in path_prefixes)

    @staticmethod
    def _normalize_tool_name(tool_name: str | None) -> str:
        normalized = (tool_name or "").strip().lower()
        if not normalized:
            return "tscan"

        aliases = {
            "memcheck": "valgrind",
            "helgrind": "valgrind",
            "drd": "valgrind",
            "threadsanitizer": "tsan",
            "thread-sanitizer": "tsan",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _normalize_sub_module(sub_module: str | None) -> str:
        return (sub_module or "").strip()

    @staticmethod
    def _as_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _as_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_detail_payload(item: dict) -> dict:
        return {
            "file_path": ScanService._as_text(item.get("file_path")) or "unknown",
            "defect_type": ScanService._as_text(item.get("defect_type")) or "Unknown",
            "severity": ScanService._as_text(item.get("severity")) or "Low",
            "description": ScanService._as_text(item.get("description")),
            "help_info": ScanService._as_text(item.get("help_info")),
            "code_snippet": ScanService._as_text(item.get("code_snippet")),
        }

    @staticmethod
    def build_fingerprint(item: dict) -> str:
        payload = ScanService._normalize_detail_payload(item)
        fingerprint_str = (
            f"{payload['file_path']}:{payload['defect_type']}:{payload['description']}"
        )
        return hashlib.md5(fingerprint_str.encode()).hexdigest()

    @staticmethod
    def build_detail_hash(payload: dict) -> str:
        normalized = {
            "file_path": payload.get("file_path") or "",
            "defect_type": payload.get("defect_type") or "",
            "severity": payload.get("severity") or "",
            "description": payload.get("description") or "",
            "help_info": payload.get("help_info") or "",
            "code_snippet": payload.get("code_snippet") or "",
        }
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_details(detail_payloads: list[dict]) -> dict[str, ScanResultDetail]:
        payload_by_hash: dict[str, dict] = {}
        for payload in detail_payloads:
            content_hash = ScanService.build_detail_hash(payload)
            payload_by_hash.setdefault(content_hash, payload)

        if not payload_by_hash:
            return {}

        existing = ScanResultDetail.objects.in_bulk(
            payload_by_hash.keys(),
            field_name="content_hash",
        )
        update_time = timezone.now()
        missing = [
            ScanResultDetail(content_hash=content_hash, updated_at=update_time, **payload)
            for content_hash, payload in payload_by_hash.items()
            if content_hash not in existing
        ]
        if missing:
            ScanResultDetail.objects.bulk_create(missing, ignore_conflicts=True)
            existing = ScanResultDetail.objects.in_bulk(
                payload_by_hash.keys(),
                field_name="content_hash",
            )
        return existing

    @staticmethod
    def _ensure_findings(
        project: ScanProject,
        entries: list[dict],
    ) -> dict[str, ScanFinding]:
        fingerprints = list(dict.fromkeys(entry["fingerprint"] for entry in entries))
        if not fingerprints:
            return {}

        existing = {
            item.fingerprint: item
            for item in ScanFinding.objects.filter(
                project=project,
                fingerprint__in=fingerprints,
            )
        }
        first_entry_by_fingerprint: dict[str, dict] = {}
        for entry in entries:
            first_entry_by_fingerprint.setdefault(entry["fingerprint"], entry)

        missing = []
        for fingerprint, entry in first_entry_by_fingerprint.items():
            if fingerprint in existing:
                continue
            seen_at = entry.get("seen_at") or timezone.now()
            task = entry.get("task")
            missing.append(
                ScanFinding(
                    project=project,
                    fingerprint=fingerprint,
                    first_seen_task=task,
                    last_seen_task=task,
                    first_seen_at=seen_at,
                    last_seen_at=seen_at,
                    updated_at=seen_at,
                )
            )
        if missing:
            ScanFinding.objects.bulk_create(missing, ignore_conflicts=True)
            existing = {
                item.fingerprint: item
                for item in ScanFinding.objects.filter(
                    project=project,
                    fingerprint__in=fingerprints,
                )
            }

        latest_entry_by_fingerprint: dict[str, dict] = {}
        earliest_entry_by_fingerprint: dict[str, dict] = {}
        for entry in entries:
            fingerprint = entry["fingerprint"]
            seen_at = entry.get("seen_at") or timezone.now()
            if (
                fingerprint not in latest_entry_by_fingerprint
                or seen_at >= latest_entry_by_fingerprint[fingerprint]["seen_at"]
            ):
                latest_entry_by_fingerprint[fingerprint] = {**entry, "seen_at": seen_at}
            if (
                fingerprint not in earliest_entry_by_fingerprint
                or seen_at < earliest_entry_by_fingerprint[fingerprint]["seen_at"]
            ):
                earliest_entry_by_fingerprint[fingerprint] = {**entry, "seen_at": seen_at}

        findings_to_update = []
        update_time = timezone.now()
        for fingerprint, finding in existing.items():
            changed = False
            latest_entry = latest_entry_by_fingerprint.get(fingerprint)
            if latest_entry and latest_entry["seen_at"] >= finding.last_seen_at:
                finding.last_seen_task = latest_entry.get("task")
                finding.last_seen_at = latest_entry["seen_at"]
                changed = True

            earliest_entry = earliest_entry_by_fingerprint.get(fingerprint)
            if earliest_entry and earliest_entry["seen_at"] < finding.first_seen_at:
                finding.first_seen_task = earliest_entry.get("task")
                finding.first_seen_at = earliest_entry["seen_at"]
                changed = True

            if finding.is_deleted:
                finding.is_deleted = False
                changed = True

            if changed:
                finding.updated_at = update_time
                findings_to_update.append(finding)

        if findings_to_update:
            ScanFinding.objects.bulk_update(
                findings_to_update,
                [
                    "first_seen_task",
                    "first_seen_at",
                    "last_seen_task",
                    "last_seen_at",
                    "is_deleted",
                    "updated_at",
                ],
            )
        return existing

    @staticmethod
    def _shielded_fingerprints(project: ScanProject, fingerprints: list[str]) -> set[str]:
        if not fingerprints:
            return set()

        normalized = list(dict.fromkeys(fingerprints))
        from_findings = set(
            ScanFinding.objects.filter(
                project=project,
                fingerprint__in=normalized,
                shield_status="Shielded",
                is_deleted=False,
            ).values_list("fingerprint", flat=True)
        )
        from_legacy_results = set(
            ScanResult.objects.filter(
                task__project=project,
                fingerprint__in=normalized,
                shield_status="Shielded",
                is_deleted=False,
                task__is_deleted=False,
            ).values_list("fingerprint", flat=True)
        )
        return from_findings | from_legacy_results

    @staticmethod
    def persist_normalized_results(
        task: ScanTask,
        defects: list[dict],
        *,
        replace_task: bool = False,
        legacy_results: list[ScanResult] | None = None,
    ) -> int:
        project_prefix_rules = ScanService._normalize_path_prefixes(
            getattr(task.project, "path_shield_prefixes", []),
        )
        legacy_results = legacy_results or []
        legacy_by_index = {index: result for index, result in enumerate(legacy_results)}

        entries: list[dict] = []
        detail_payloads: list[dict] = []
        fingerprints: list[str] = []
        for index, item in enumerate(defects):
            legacy_result = legacy_by_index.get(index)
            detail_payload = ScanService._normalize_detail_payload(item)
            fingerprint = (
                legacy_result.fingerprint if legacy_result else ScanService.build_fingerprint(item)
            )
            seen_at = (
                getattr(legacy_result, "sys_create_datetime", None)
                or getattr(task, "sys_create_datetime", None)
                or timezone.now()
            )
            entry = {
                "task": task,
                "detail_payload": detail_payload,
                "fingerprint": fingerprint,
                "line_number": ScanService._as_int(item.get("line_number"), 0),
                "legacy_result": legacy_result,
                "seen_at": seen_at,
                "path_rule_shielded": ScanService._is_path_prefix_shielded(
                    detail_payload["file_path"],
                    project_prefix_rules,
                ),
            }
            entries.append(entry)
            detail_payloads.append(detail_payload)
            fingerprints.append(fingerprint)

        if replace_task:
            ScanResultOccurrence.objects.filter(task=task).delete()

        if not entries:
            return 0

        details = ScanService._ensure_details(detail_payloads)
        findings = ScanService._ensure_findings(task.project, entries)
        inherited_shielded = ScanService._shielded_fingerprints(task.project, fingerprints)

        occurrences: list[ScanResultOccurrence] = []
        finding_status_updates: dict[int, str] = {}
        for entry in entries:
            detail_hash = ScanService.build_detail_hash(entry["detail_payload"])
            finding = findings[entry["fingerprint"]]
            legacy_result = entry["legacy_result"]
            if legacy_result:
                status = legacy_result.shield_status
            else:
                status = (
                    "Shielded"
                    if entry["fingerprint"] in inherited_shielded or entry["path_rule_shielded"]
                    else "Normal"
                )

            if status != "Normal":
                previous = finding_status_updates.get(finding.id)
                if previous != "Shielded":
                    finding_status_updates[finding.id] = status

            occurrences.append(
                ScanResultOccurrence(
                    task=task,
                    finding=finding,
                    detail=details[detail_hash],
                    legacy_result=legacy_result,
                    line_number=entry["line_number"],
                    shield_status=status,
                    created_at=entry["seen_at"],
                    updated_at=entry["seen_at"],
                )
            )

        ScanResultOccurrence.objects.bulk_create(occurrences)

        if finding_status_updates:
            findings_to_update = []
            update_time = timezone.now()
            for finding in findings.values():
                next_status = finding_status_updates.get(finding.id)
                if not next_status:
                    continue
                if finding.shield_status == "Shielded" and next_status != "Shielded":
                    continue
                finding.shield_status = next_status
                finding.updated_at = update_time
                findings_to_update.append(finding)
            if findings_to_update:
                ScanFinding.objects.bulk_update(
                    findings_to_update,
                    ["shield_status", "updated_at"],
                )

        return len(occurrences)
    
    @staticmethod
    def create_project(data: dict, user: User) -> ScanProject:
        """创建扫描项目"""
        payload = dict(data)
        payload["caretaker_id"] = payload.get("caretaker_id") or None
        payload["path_shield_prefixes"] = ScanService._normalize_path_prefixes(
            payload.get("path_shield_prefixes"),
        )
        return ScanProject.objects.create(**payload, sys_creator=user)

    @staticmethod
    def update_project(project_id: str, data: dict, user: User) -> ScanProject:
        """更新扫描项目"""
        project = get_object_or_404(ScanProject.objects.filter(is_deleted=False), id=project_id)
        payload = dict(data)
        payload["caretaker_id"] = payload.get("caretaker_id") or None
        if "path_shield_prefixes" in payload:
            payload["path_shield_prefixes"] = ScanService._normalize_path_prefixes(
                payload.get("path_shield_prefixes"),
            )
        for key, value in payload.items():
            setattr(project, key, value)
        project.sys_modifier = user
        project.save()
        return project

    @staticmethod
    @transaction.atomic
    def delete_project(project_id: str, user: User) -> bool:
        """删除扫描项目，并同步软删除关联任务/结果/屏蔽申请。"""
        project = get_object_or_404(
            ScanProject.objects.filter(is_deleted=False),
            id=project_id,
        )
        modifier_id = getattr(user, "id", None)
        ScanService._soft_delete_queryset(
            ShieldApplication.objects.filter(
                Q(result__task__project=project) | Q(occurrence__task__project=project),
            ),
            modifier_id,
        )
        ScanService._soft_delete_light_queryset(
            ScanResultOccurrence.objects.filter(task__project=project),
        )
        ScanService._soft_delete_light_queryset(
            ScanFinding.objects.filter(project=project),
        )
        ScanService._soft_delete_queryset(
            ScanResult.objects.filter(task__project=project),
            modifier_id,
        )
        ScanService._soft_delete_queryset(
            ScanTask.objects.filter(project=project),
            modifier_id,
        )
        project.is_deleted = True
        project.sys_modifier = user
        project.save(update_fields=["is_deleted", "sys_modifier", "sys_update_datetime"])
        return True

    @staticmethod
    def handle_upload(
        project_key: str,
        tool_name: str,
        file_obj,
        sub_module: str | None = None,
    ) -> ScanTask:
        """接收文件上传并触发解析"""
        normalized_tool = ScanService._normalize_tool_name(tool_name)
        normalized_sub_module = ScanService._normalize_sub_module(sub_module)
        try:
            project = ScanProject.objects.get(project_key=project_key, is_deleted=False)
        except ScanProject.DoesNotExist:
            raise ValueError("无效的项目标识 (project_key)")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"scan_reports/{project.id}/{timestamp}_{normalized_tool}_{file_obj.name}"
        saved_path = default_storage.save(file_name, ContentFile(file_obj.read()))
        full_path = os.path.join(settings.MEDIA_ROOT, saved_path)

        task = ScanTask.objects.create(
            project=project,
            tool_name=normalized_tool,
            status="processing",
            source="pipeline",
            report_file=full_path,
            scan_time=datetime.now(),
            sub_module=normalized_sub_module,
        )

        try:
            ScanService.process_report(task.id)
        except Exception as e:
            logger.error(f"任务 {task.id} 异步处理失败: {e}")
            task.status = "failed"
            task.log = str(e)
            task.save()

        task.refresh_from_db()
        return task

    @staticmethod
    def handle_chunk_upload(
        project_key: str,
        tool_name: str,
        chunk_index: int,
        total_chunks: int,
        chunk_content: str,
        file_id: str,
        file_ext: str = None,
        sub_module: str | None = None,
    ) -> dict:
        """
        处理分片上传的 JSON 文本内容
        """
        normalized_tool = ScanService._normalize_tool_name(tool_name)
        normalized_sub_module = ScanService._normalize_sub_module(sub_module)
        try:
            project = ScanProject.objects.get(project_key=project_key, is_deleted=False)
        except ScanProject.DoesNotExist:
            raise ValueError("无效的项目标识 (project_key)")

        # 使用缓存或临时文件存储分片
        # 键格式: scan_upload:{file_id}:{chunk_index}
        # 假设已配置 Redis 缓存
        from django.core.cache import cache
        
        cache_key = f"scan_upload:{file_id}:{chunk_index}"
        cache.set(cache_key, chunk_content, timeout=3600) # 超时时间 1 小时
        
        # 检查是否接收到所有分片
        received_chunks = 0
        for i in range(total_chunks):
            if cache.get(f"scan_upload:{file_id}:{i}"):
                received_chunks += 1
        
        if received_chunks == total_chunks:
            # 合并所有分片
            full_content = ""
            for i in range(total_chunks):
                full_content += cache.get(f"scan_upload:{file_id}:{i}")
                cache.delete(f"scan_upload:{file_id}:{i}") # 清理缓存
            
            # 保存到文件
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            file_ext = (file_ext or "").strip().lower().lstrip(".")
            # 兼容处理 file_ext，默认使用 xml (针对 tscancode)
            if not file_ext:
                if normalized_tool in ["tscan", "cppcheck"]:
                    file_ext = "xml"
                elif normalized_tool in ["cooddy"]:
                    file_ext = "csv"
                elif normalized_tool in ["valgrind"]:
                    file_ext = "log"
                elif normalized_tool in ["tsan"]:
                    file_ext = "log"
                elif normalized_tool in ["weggli", "binexplorer", "clang-tidy", "clang_tidy", "clangtidy"]:
                    file_ext = "xlsx"
                else:
                    file_ext = "json"
            
            payload_bytes = full_content.encode("utf-8")
            if file_ext in {"xlsx", "xls"}:
                try:
                    payload_bytes = base64.b64decode(full_content, validate=True)
                except (binascii.Error, ValueError):
                    payload_bytes = full_content.encode("utf-8")

            file_name = f"scan_reports/{project.id}/{timestamp}_{normalized_tool}_{file_id}.{file_ext}"
            saved_path = default_storage.save(file_name, ContentFile(payload_bytes))
            full_path = os.path.join(settings.MEDIA_ROOT, saved_path)
            
            # 创建扫描任务
            task = ScanTask.objects.create(
                project=project,
                tool_name=normalized_tool,
                status='processing',
                source='pipeline',
                report_file=full_path,
                scan_time=datetime.now(),
                sub_module=normalized_sub_module,
            )
            
            # 触发解析处理
            try:
                ScanService.process_report(task.id)
            except Exception as e:
                logger.error(f"任务 {task.id} 异步处理失败: {e}")
                task.status = 'failed'
                task.log = str(e)
                task.save()
            
            return {"status": "completed", "task_id": str(task.id)}
        
        return {"status": "chunk_received", "received": received_chunks, "total": total_chunks}

    @staticmethod
    def process_report(task_id: str):
        """
        解析报告并保存结果
        """
        task = ScanTask.objects.get(id=task_id)
        try:
            parser = ParserFactory.get_parser(task.tool_name)
            defects = parser.parse(task.report_file)
            
            with transaction.atomic():
                ScanService.persist_normalized_results(
                    task,
                    defects,
                    replace_task=True,
                )
                
            task.status = 'success'
            task.processed_time = datetime.now()
            task.log = f"成功解析 {len(defects)} 个缺陷。"
            task.save()
            
        except Exception as e:
            task.status = 'failed'
            task.log = f"处理失败: {str(e)}"
            task.save()
            logger.exception(f"处理任务 {task_id} 失败")

    @staticmethod
    def apply_shield(user, result_ids, approver_id, reason):
        """申请屏蔽缺陷"""
        approver = User.objects.get(id=approver_id)
        normalized_ids = [str(item) for item in (result_ids or []) if str(item).isdigit()]
        legacy_ids = [str(item) for item in (result_ids or []) if not str(item).isdigit()]
        occurrences = ScanResultOccurrence.objects.filter(
            id__in=normalized_ids,
            is_deleted=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        ).select_related("finding", "legacy_result")
        results = ScanResult.objects.filter(id__in=legacy_ids, is_deleted=False)
        
        with transaction.atomic():
            for occurrence in occurrences:
                if occurrence.shield_status != 'Normal':
                    continue
                occurrence.shield_status = 'Pending'
                occurrence.save(update_fields=['shield_status', 'updated_at'])
                occurrence.finding.shield_status = 'Pending'
                occurrence.finding.save(update_fields=['shield_status', 'updated_at'])

                if occurrence.legacy_result_id:
                    occurrence.legacy_result.shield_status = 'Pending'
                    occurrence.legacy_result.save(update_fields=['shield_status', 'sys_update_datetime'])

                ShieldApplication.objects.create(
                    result=occurrence.legacy_result,
                    occurrence=occurrence,
                    applicant=user,
                    approver=approver,
                    reason=reason,
                    status='Pending'
                )

            for result in results:
                if result.shield_status == 'Normal':
                    result.shield_status = 'Pending'
                    result.save(update_fields=['shield_status', 'sys_update_datetime'])

                    try:
                        occurrence = result.normalized_occurrence
                    except ScanResultOccurrence.DoesNotExist:
                        occurrence = None
                    if occurrence:
                        occurrence.shield_status = 'Pending'
                        occurrence.save(update_fields=['shield_status', 'updated_at'])
                        occurrence.finding.shield_status = 'Pending'
                        occurrence.finding.save(update_fields=['shield_status', 'updated_at'])
                    
                    ShieldApplication.objects.create(
                        result=result,
                        occurrence=occurrence,
                        applicant=user,
                        approver=approver,
                        reason=reason,
                        status='Pending'
                    )

    @staticmethod
    def audit_shield(user, application_id, status, comment):
        """审批屏蔽申请"""
        app = ShieldApplication.objects.select_related(
            'result',
            'occurrence',
            'occurrence__finding',
        ).get(id=application_id, approver=user)
        
        with transaction.atomic():
            app.status = status
            app.audit_comment = comment
            app.save(update_fields=['status', 'audit_comment', 'sys_update_datetime'])
            
            ScanService._apply_audit_status_to_result(app, status)

    @staticmethod
    def _apply_audit_status_to_result(app: ShieldApplication, status: str):
        next_status = 'Shielded' if status == 'Approved' else 'Rejected'
        if app.occurrence_id:
            app.occurrence.shield_status = next_status
            app.occurrence.save(update_fields=['shield_status', 'updated_at'])
            app.occurrence.finding.shield_status = next_status
            app.occurrence.finding.save(update_fields=['shield_status', 'updated_at'])

        if app.result_id:
            app.result.shield_status = next_status
            app.result.save(update_fields=['shield_status', 'sys_update_datetime'])

    @staticmethod
    def audit_shield_batch(user, application_ids, status, comment):
        """批量审批屏蔽申请"""
        if not application_ids:
            return 0

        query_set = ShieldApplication.objects.filter(
            id__in=application_ids,
            approver=user,
            is_deleted=False,
            status='Pending',
        ).select_related('result', 'occurrence', 'occurrence__finding')

        processed = 0
        with transaction.atomic():
            for app in query_set:
                app.status = status
                app.audit_comment = comment
                app.save(update_fields=['status', 'audit_comment', 'sys_update_datetime'])

                ScanService._apply_audit_status_to_result(app, status)
                processed += 1

        return processed
