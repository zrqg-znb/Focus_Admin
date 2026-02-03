import os
import shutil
import json
import hashlib
import logging
from datetime import datetime
from django.conf import settings
from django.db import transaction
from apps.tscan.models import TScanProject, TScanTask, TScanResult, TScanShieldApplication
from core.user.user_model import User

logger = logging.getLogger(__name__)

class TScanService:
    
    @staticmethod
    def run_task(task_id):
        """执行扫描任务"""
        task = TScanTask.objects.get(id=task_id)
        project = task.project
        task.status = 'running'
        task.start_time = datetime.now()
        task.save()
        
        work_dir = os.path.join(settings.BASE_DIR, 'media', 'tscan', str(task.id))
        os.makedirs(work_dir, exist_ok=True)
        
        try:
            # 1. Clone/Sync code
            # TODO: 实际生产中应使用 git 库，此处暂用模拟逻辑
            task.log = f"[{datetime.now()}] 开始拉取代码: {project.repo_url} (branch: {project.branch})\n"
            task.save()
            
            # 2. Docker Execution
            # 此处模拟调用 docker-py
            task.log += f"[{datetime.now()}] 启动 Docker 容器: {project.docker_image}\n"
            task.log += f"[{datetime.now()}] 执行编译命令: {project.build_cmd}\n"
            task.log += f"[{datetime.now()}] 执行 tscan 扫描...\n"
            task.save()
            
            # 模拟生成扫描结果文件
            result_file = os.path.join(work_dir, 'tscan_result.json')
            mock_results = [
                {
                    "file": "src/main.c",
                    "line": 10,
                    "type": "NullPointer",
                    "severity": "High",
                    "message": "Potential null pointer dereference"
                },
                {
                    "file": "src/utils.c",
                    "line": 45,
                    "type": "MemoryLeak",
                    "severity": "Medium",
                    "message": "Memory allocated at line 40 is not freed"
                }
            ]
            with open(result_file, 'w') as f:
                json.dump(mock_results, f)
            
            # 3. Parse and Save Results
            TScanService.parse_results(task, result_file)
            
            task.status = 'success'
            task.log += f"[{datetime.now()}] 扫描完成，结果已入库。\n"
        except Exception as e:
            task.status = 'failed'
            task.log += f"[{datetime.now()}] 执行失败: {str(e)}\n"
            logger.exception("TScan task failed")
        finally:
            task.end_time = datetime.now()
            task.save()
            # 清理工作目录（可选）
            # shutil.rmtree(work_dir, ignore_errors=True)

    @staticmethod
    def parse_results(task, result_file):
        """解析扫描结果并入库"""
        if not os.path.exists(result_file):
            return
            
        with open(result_file, 'r') as f:
            data = json.load(f)
            
        with transaction.atomic():
            for item in data:
                # 生成指纹：文件路径 + 类型 + 描述
                fingerprint_str = f"{item['file']}:{item['type']}:{item['message']}"
                fingerprint = hashlib.md5(fingerprint_str.encode()).hexdigest()
                
                # 检查是否存在已生效的屏蔽规则（指纹匹配且状态为已屏蔽）
                # 此处简单实现：查找该项目下该指纹是否有过已屏蔽的记录
                is_shielded = TScanResult.objects.filter(
                    task__project=task.project,
                    fingerprint=fingerprint,
                    shield_status='Shielded'
                ).exists()
                
                status = 'Shielded' if is_shielded else 'Normal'
                
                TScanResult.objects.create(
                    task=task,
                    file_path=item['file'],
                    line_number=item['line'],
                    defect_type=item['type'],
                    severity=item['severity'],
                    description=item['message'],
                    fingerprint=fingerprint,
                    shield_status=status
                )

    @staticmethod
    def apply_shield(user, result_ids, approver_id, reason):
        """申请屏蔽"""
        approver = User.objects.get(id=approver_id)
        results = TScanResult.objects.filter(id__in=result_ids)
        
        with transaction.atomic():
            for result in results:
                if result.shield_status == 'Normal':
                    result.shield_status = 'Pending'
                    result.save()
                    
                    TScanShieldApplication.objects.create(
                        result=result,
                        applicant=user,
                        approver=approver,
                        reason=reason,
                        status='Pending'
                    )

    @staticmethod
    def audit_shield(user, application_id, status, comment):
        """审批屏蔽申请"""
        app = TScanShieldApplication.objects.get(id=application_id, approver=user)
        
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
