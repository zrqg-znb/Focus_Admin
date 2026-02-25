import os
import hashlib
import logging
import base64
import binascii
from datetime import datetime
from typing import Any, Iterable
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from apps.code_scan.models import ScanProject, ScanTask, ScanResult, ShieldApplication
from apps.code_scan.parsers.factory import ParserFactory
from core.user.user_model import User

logger = logging.getLogger(__name__)

class ScanService:
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
    def create_project(data: dict, user: User) -> ScanProject:
        """创建扫描项目"""
        payload = dict(data)
        payload["path_shield_prefixes"] = ScanService._normalize_path_prefixes(
            payload.get("path_shield_prefixes"),
        )
        return ScanProject.objects.create(**payload, sys_creator=user)

    @staticmethod
    def update_project(project_id: str, data: dict, user: User) -> ScanProject:
        """更新扫描项目"""
        project = get_object_or_404(ScanProject, id=project_id)
        payload = dict(data)
        if "path_shield_prefixes" in payload:
            payload["path_shield_prefixes"] = ScanService._normalize_path_prefixes(
                payload.get("path_shield_prefixes"),
            )
        for key, value in payload.items():
            setattr(project, key, value)
        project.save()
        return project

    @staticmethod
    def handle_upload(project_key: str, tool_name: str, file_obj) -> ScanTask:
        """接收文件上传并触发解析"""
        normalized_tool = (tool_name or "").strip().lower()
        if not normalized_tool:
            normalized_tool = "tscan"
        try:
            project = ScanProject.objects.get(project_key=project_key)
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
        )

        try:
            ScanService.process_report(task.id)
        except Exception as e:
            logger.error(f"任务 {task.id} 异步处理失败: {e}")
            task.status = "failed"
            task.log = str(e)
            task.save()

        return task

    @staticmethod
    def handle_chunk_upload(project_key: str, tool_name: str, chunk_index: int, total_chunks: int, chunk_content: str, file_id: str, file_ext: str = None) -> dict:
        """
        处理分片上传的 JSON 文本内容
        """
        normalized_tool = (tool_name or "").strip().lower()
        if not normalized_tool:
            normalized_tool = "tscan"
        try:
            project = ScanProject.objects.get(project_key=project_key)
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
                scan_time=datetime.now()
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
            project_prefix_rules = ScanService._normalize_path_prefixes(
                getattr(task.project, "path_shield_prefixes", []),
            )
            
            with transaction.atomic():
                # 如果是重跑任务，清除旧结果
                ScanResult.objects.filter(task=task).delete()
                
                results_to_create = []
                for item in defects:
                    # 生成指纹: 文件路径 + 缺陷类型 + 描述 (不包含行号，以支持代码移动)
                    # 如果需要区分同一文件中的相同错误，建议工具提供更稳定的 context hash
                    fingerprint_str = f"{item['file_path']}:{item['defect_type']}:{item['description']}"
                    fingerprint = hashlib.md5(fingerprint_str.encode()).hexdigest()
                    
                    # 自动匹配屏蔽规则 (同项目 + 同指纹 + 已屏蔽状态)
                    is_shielded = ScanResult.objects.filter(
                        task__project=task.project,
                        fingerprint=fingerprint,
                        shield_status='Shielded'
                    ).exists()

                    is_path_rule_shielded = ScanService._is_path_prefix_shielded(
                        item['file_path'],
                        project_prefix_rules,
                    )
                    
                    status = 'Shielded' if (is_shielded or is_path_rule_shielded) else 'Normal'
                    
                    results_to_create.append(ScanResult(
                        task=task,
                        file_path=item['file_path'],
                        line_number=item['line_number'],
                        defect_type=item['defect_type'],
                        severity=item['severity'],
                        description=item['description'],
                        fingerprint=fingerprint,
                        shield_status=status,
                        help_info=item.get('help_info'),
                        code_snippet=item.get('code_snippet')
                    ))
                
                ScanResult.objects.bulk_create(results_to_create)
                
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
        results = ScanResult.objects.filter(id__in=result_ids)
        
        with transaction.atomic():
            for result in results:
                if result.shield_status == 'Normal':
                    result.shield_status = 'Pending'
                    result.save()
                    
                    ShieldApplication.objects.create(
                        result=result,
                        applicant=user,
                        approver=approver,
                        reason=reason,
                        status='Pending'
                    )

    @staticmethod
    def audit_shield(user, application_id, status, comment):
        """审批屏蔽申请"""
        app = ShieldApplication.objects.get(id=application_id, approver=user)
        
        with transaction.atomic():
            app.status = status
            app.audit_comment = comment
            app.save()
            
            result = app.result
            if status == 'Approved':
                result.shield_status = 'Shielded'
            else:
                result.shield_status = 'Rejected'
            result.save()

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
        ).select_related('result')

        processed = 0
        with transaction.atomic():
            for app in query_set:
                app.status = status
                app.audit_comment = comment
                app.save(update_fields=['status', 'audit_comment', 'sys_update_datetime'])

                result = app.result
                if status == 'Approved':
                    result.shield_status = 'Shielded'
                else:
                    result.shield_status = 'Rejected'
                result.save(update_fields=['shield_status', 'sys_update_datetime'])
                processed += 1

        return processed
