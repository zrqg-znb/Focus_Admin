import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.ci_daily_report.models import ProjectConfig, ProjectDailyData

class Command(BaseCommand):
    help = 'Generate mock data for CI Daily Report'

    def handle(self, *args, **options):
        self.stdout.write("Generating mock data...")
        
        # 1. 创建项目
        projects = [
            {"name": "Focus-Backend", "category": "后端", "owner": "ZhangSan", "desc": "核心后端服务"},
            {"name": "Focus-Frontend", "category": "前端", "owner": "LiSi", "desc": "管理后台前端"},
            {"name": "Focus-Mobile", "category": "移动端", "owner": "WangWu", "desc": "移动APP"},
            {"name": "Data-Center", "category": "大数据", "owner": "ZhaoLiu", "desc": "数据中台"},
            {"name": "AI-Model", "category": "算法", "owner": "SunQi", "desc": "AI模型训练"},
        ]
        
        db_projects = []
        for p in projects:
            obj, created = ProjectConfig.objects.get_or_create(
                name=p["name"],
                defaults={
                    "description": p["desc"],
                    "project_category": p["category"],
                    "project_owner": p["owner"],
                    "codecheck_id": f"cc_{random.randint(1000, 9999)}",
                }
            )
            if created:
                self.stdout.write(f"Created project: {obj.name}")
            db_projects.append(obj)
            
        # 2. 生成最近30天的数据
        today = date.today()
        for project in db_projects:
            for i in range(30):
                day = today - timedelta(days=i)
                
                # 随机生成数据
                total_cases = random.randint(500, 2000)
                pass_rate = random.uniform(0.85, 1.0)
                passed_cases = int(total_cases * pass_rate)
                
                ProjectDailyData.objects.update_or_create(
                    project=project,
                    date=day,
                    defaults={
                        "test_cases_count": total_cases,
                        "test_cases_passed": passed_cases,
                        "compile_standard_options": {
                            "warnings": random.randint(0, 50),
                            "errors": 0,
                            "style_issues": random.randint(0, 20)
                        },
                        "build_standard_options": {
                            "duration_min": random.randint(5, 45),
                            "success": True
                        },
                        "extra_data": {
                            "code_coverage": f"{random.randint(60, 95)}%",
                            "bugs_open": random.randint(0, 15)
                        }
                    }
                )
                
        self.stdout.write(self.style.SUCCESS("Mock data generated successfully!"))
