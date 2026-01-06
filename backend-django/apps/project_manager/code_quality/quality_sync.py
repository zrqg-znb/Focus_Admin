from datetime import date, timedelta
import random
from apps.project_manager.code_quality.code_quality_model import CodeModule, CodeMetric
from apps.project_manager.project.project_model import Project

class CodeQualityMock:
    @staticmethod
    def get_module_metrics(oem_name: str, module_name: str):
        """
        模拟从数据中台获取代码模块的质量指标
        """
        return {
            "loc": random.randint(1000, 50000),
            "function_count": random.randint(50, 1000),
            "dangerous_func_count": random.randint(0, 50),
            "duplication_rate": round(random.uniform(0.0, 20.0), 2)
        }

def sync_project_quality_metrics(project: Project):
    """
    同步单个项目的代码质量数据
    """
    if not project.enable_quality:
        return

    # 获取该项目的所有配置模块
    modules = CodeModule.objects.filter(project=project, is_deleted=False)
    
    today = date.today()
    
    for module in modules:
        # 模拟获取指标
        metrics_data = CodeQualityMock.get_module_metrics(module.oem_name, module.module)
        
        # 保存指标数据 (记录为今天的数据)
        CodeMetric.objects.update_or_create(
            module=module,
            record_date=today,
            defaults=metrics_data
        )

def sync_all_projects_quality():
    """
    定时任务调用：同步所有开启了代码质量统计的项目
    """
    projects = Project.objects.filter(
        enable_quality=True,
        is_deleted=False,
        is_closed=False
    )
    
    for project in projects:
        try:
            sync_project_quality_metrics(project)
        except Exception as e:
            print(f"Failed to sync quality for project {project.name}: {e}")
