from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
import random
import logging

from .models import ProjectConfig, ProjectDailyData, Subscription

logger = logging.getLogger(__name__)
User = get_user_model()

def mock_fetch_data_from_platform(config: ProjectConfig) -> dict:
    """
    模拟从数据中台获取数据。
    实际开发中请替换为真实的API请求。
    """
    logger.info(f"Fetching data for project: {config.name} (CodeCheckID: {config.codecheck_id})")
    
    # 模拟数据
    total_cases = random.randint(500, 2000)
    passed_cases = int(total_cases * random.uniform(0.8, 1.0))
    
    return {
        "test_cases_count": total_cases,
        "test_cases_passed": passed_cases,
        "compile_standard_options": {"warnings": random.randint(0, 50), "errors": 0},
        "build_standard_options": {"duration": f"{random.randint(10, 60)}m"},
        "extra_data": {
            "codecov": f"{random.randint(50, 90)}%",
            "fossbot_issues": random.randint(0, 10)
        }
    }

@shared_task
def fetch_daily_project_data():
    """
    定时任务：每天获取所有配置项目的最新数据
    """
    logger.info("Starting daily project data fetch...")
    today = timezone.now().date()
    configs = ProjectConfig.objects.all()
    
    count = 0
    for config in configs:
        try:
            data = mock_fetch_data_from_platform(config)
            
            ProjectDailyData.objects.update_or_create(
                project=config,
                date=today,
                defaults=data
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to fetch data for project {config.name}: {e}")
            
    logger.info(f"Completed data fetch. Updated {count} projects.")
    return f"Fetched data for {count} projects"


@shared_task
def send_daily_subscription_emails():
    """
    定时任务：向订阅用户发送日报邮件
    """
    logger.info("Starting daily email dispatch...")
    today = timezone.now().date()
    
    # 获取所有有订阅的用户
    # 这里优化查询，只查找有激活订阅的用户
    users_with_subs = User.objects.filter(
        subscriptions__is_active=True
    ).distinct()
    
    sent_count = 0
    
    for user in users_with_subs:
        # 获取该用户订阅的所有项目
        subscriptions = Subscription.objects.filter(user=user, is_active=True).select_related('project')
        
        if not subscriptions.exists():
            continue
            
        # 收集这些项目今天的最新数据
        report_data = []
        for sub in subscriptions:
            project = sub.project
            # 尝试获取今日数据，如果没有则获取最近一次的数据
            daily_data = ProjectDailyData.objects.filter(project=project, date=today).first()
            
            if not daily_data:
                # 如果今日数据还没抓取，可能任务顺序问题，或者获取失败
                # 尝试获取昨天的，或者跳过
                daily_data = ProjectDailyData.objects.filter(project=project).order_by('-date').first()
                
            if daily_data:
                report_data.append({
                    "project_name": project.name,
                    "date": daily_data.date,
                    "test_total": daily_data.test_cases_count,
                    "test_passed": daily_data.test_cases_passed,
                    "pass_rate": f"{(daily_data.test_cases_passed / daily_data.test_cases_count * 100):.1f}%" if daily_data.test_cases_count > 0 else "0%",
                    "extra": daily_data.extra_data
                })
        
        if not report_data:
            logger.warning(f"No data found for user {user.username}'s subscriptions.")
            continue
            
        # 构建邮件内容
        # 简单起见，这里直接构建HTML字符串，实际可以使用Django Template
        email_subject = f"【项目日报】{today} - 您订阅的项目数据概览"
        email_body = f"""
        <html>
        <body>
            <h2>你好, {user.username}</h2>
            <p>这是您订阅的项目在 {today} 的数据概览：</p>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>项目名称</th>
                    <th>日期</th>
                    <th>测试用例总数</th>
                    <th>通过数</th>
                    <th>通过率</th>
                    <th>其他信息</th>
                </tr>
        """
        
        for item in report_data:
            email_body += f"""
                <tr>
                    <td>{item['project_name']}</td>
                    <td>{item['date']}</td>
                    <td>{item['test_total']}</td>
                    <td>{item['test_passed']}</td>
                    <td>{item['pass_rate']}</td>
                    <td>{item['extra']}</td>
                </tr>
            """
            
        email_body += """
            </table>
            <p>请登录系统查看更多详情。</p>
        </body>
        </html>
        """
        
        try:
            send_mail(
                subject=email_subject,
                message="", # 纯文本版本留空
                html_message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {e}")
            
    logger.info(f"Sent emails to {sent_count} users.")
    return f"Sent {sent_count} emails"
