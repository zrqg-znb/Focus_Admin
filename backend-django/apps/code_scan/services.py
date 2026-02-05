import os
import hashlib
import logging
from datetime import datetime
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
    def create_project(data: dict, user: User) -> ScanProject:
        """创建扫描项目"""
        return ScanProject.objects.create(**data, sys_creator=user)

    @staticmethod
    def update_project(project_id: str, data: dict, user: User) -> ScanProject:
        """更新扫描项目"""
        project = get_object_or_404(ScanProject, id=project_id)
        for key, value in data.items():
            setattr(project, key, value)
        project.save()
        return project

    @staticmethod
    def handle_upload(project_key: str, tool_name: str, file_obj) -> ScanTask:
        """接收文件上传并触发解析"""
        try:
            project = ScanProject.objects.get(project_key=project_key)
        except ScanProject.DoesNotExist:
            raise ValueError("无效的项目标识 (project_key)")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"scan_reports/{project.id}/{timestamp}_{tool_name}_{file_obj.name}"
        saved_path = default_storage.save(file_name, ContentFile(file_obj.read()))
        full_path = os.path.join(settings.MEDIA_ROOT, saved_path)

        task = ScanTask.objects.create(
            project=project,
            tool_name=tool_name,
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
    def handle_chunk_upload(project_key: str, tool_name: str, chunk_index: int, total_chunks: int, chunk_content: str, file_id: str, file_ext: str = "xml") -> dict:
        """
        处理分片上传的 JSON 文本内容
        """
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
            # 兼容处理 file_ext，默认使用 xml (针对 tscancode)
            if not file_ext:
                file_ext = "xml" if tool_name == "tscan" else "json"
            
            file_name = f"scan_reports/{project.id}/{timestamp}_{tool_name}_{file_id}.{file_ext}"
            saved_path = default_storage.save(file_name, ContentFile(full_content.encode('utf-8')))
            full_path = os.path.join(settings.MEDIA_ROOT, saved_path)
            
            # 创建扫描任务
            task = ScanTask.objects.create(
                project=project,
                tool_name=tool_name,
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
                    
                    status = 'Shielded' if is_shielded else 'Normal'
                    
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
