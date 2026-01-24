
import csv
import random
import uuid
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.code_compliance.models import ComplianceRecord
from core.user.user_model import User
from core.dept.dept_model import Dept

class Command(BaseCommand):
    help = 'Load mock compliance data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Start loading mock data...')
        
        # Create some departments if not exist
        dept_names = ['研发一部', '研发二部', '测试部', '产品部', '运维部']
        depts = []
        for name in dept_names:
            dept, _ = Dept.objects.get_or_create(name=name, defaults={'code': f'D{random.randint(100,999)}'})
            depts.append(dept)
            
        # Create some users if not exist (linking to depts)
        users = []
        for i in range(20):
            gitee_id = f"z600944{i:02d}"
            username = f"user_{gitee_id}"
            dept = random.choice(depts)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'name': f"User {i}",
                    'gitee_id': gitee_id,
                    'dept': dept,
                    'password': 'password'
                }
            )
            if not user.gitee_id:
                user.gitee_id = gitee_id
                user.dept = dept
                user.save()
            users.append(user)
            
        # Generate mock records
        # user	ChangeaId	Title	UpdateTime	Url	Missing branches
        # z60094428	l1e86ed7a643fdbdf7b191eff5d2b23f9c3ad464d	TicketNo：AR20251101xxxx	2025/11/1 17:43	 `http://mgit-tm.rnd.huawei.com/#/3007579` 	['br_release_icsp_5.0','br_release_2.0']
        
        ComplianceRecord.objects.all().delete()
        
        records = []
        for _ in range(100):
            user = random.choice(users)
            change_id = uuid.uuid4().hex
            ticket_no = f"AR{random.randint(20240000, 20259999)}"
            update_time = timezone.now() - timedelta(days=random.randint(0, 30))
            url = f"http://mgit-tm.rnd.huawei.com/#/{random.randint(1000000, 9999999)}"
            missing_branches = [f"br_release_{random.randint(1,5)}.0", f"br_release_icsp_{random.randint(1,5)}.0"]
            
            # Random status
            status = random.choices([0, 1, 2], weights=[0.6, 0.2, 0.2])[0]
            
            record = ComplianceRecord(
                user=user,
                change_id=change_id,
                title=f"TicketNo：{ticket_no}",
                update_time=update_time,
                url=url,
                missing_branches=missing_branches,
                status=status
            )
            records.append(record)
            
        ComplianceRecord.objects.bulk_create(records)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(records)} compliance records'))
