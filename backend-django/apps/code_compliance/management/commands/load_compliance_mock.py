
import random
import uuid
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.code_compliance.models import ComplianceRecord, ComplianceBranch
from core.user.user_model import User
from core.post.post_model import Post

class Command(BaseCommand):
    help = 'Load mock compliance data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Start loading mock data...')
        
        # 1. Create Posts (岗位)
        post_names = ['后端开发工程师', '前端开发工程师', '测试工程师', '产品经理', '运维工程师', '系统架构师']
        posts = []
        for i, name in enumerate(post_names):
            post, _ = Post.objects.get_or_create(
                code=f'P{i+1:03d}',
                defaults={
                    'name': name,
                    'post_type': 1 if '开发' in name or '架构' in name else (2 if '产品' in name else 4),
                    'status': True
                }
            )
            posts.append(post)
            
        self.stdout.write(f'Created/Loaded {len(posts)} posts.')

        # 2. Create Users and assign Posts
        users = []
        for i in range(20):
            gitee_id = f"z600944{i:02d}"
            username = f"user_{gitee_id}"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'name': f"User {i}",
                    'gitee_id': gitee_id,
                    'password': 'password', # password will be hashed by save() in User model if not hashed
                    'user_status': 1,
                    'is_active': True
                }
            )
            # Assign random post (clear existing first to avoid accumulation in multiple runs)
            user.post.clear()
            user.post.add(random.choice(posts))
            users.append(user)
            
        self.stdout.write(f'Created/Loaded {len(users)} users.')

        # 3. Generate Compliance Records and Branches
        # Clear existing records
        ComplianceRecord.objects.all().delete()
        
        records_count = 0
        branches_count = 0
        
        for _ in range(100):
            user = random.choice(users)
            change_id = uuid.uuid4().hex[:12]
            ticket_no = f"AR{random.randint(20240000, 20259999)}"
            update_time = timezone.now() - timedelta(days=random.randint(0, 30))
            url = f"http://mgit-tm.rnd.huawei.com/#/{random.randint(1000000, 9999999)}"
            
            # Create Record
            record = ComplianceRecord.objects.create(
                user=user,
                change_id=change_id,
                title=f"TicketNo：{ticket_no} Fix bug related to NPE",
                update_time=update_time,
                url=url,
                status=0 # Default, will calculate below
            )
            records_count += 1
            
            # Create Branches
            branch_options = [
                f"br_release_{random.randint(1,5)}.0", 
                f"br_release_icsp_{random.randint(1,5)}.0",
                "master",
                "develop"
            ]
            # Randomly pick 1 to 3 branches
            selected_branches = random.sample(branch_options, k=random.randint(1, 3))
            
            record_branches = []
            for b_name in selected_branches:
                # Random status for branch: 0 (Unresolved), 1 (No Risk), 2 (Fixed)
                # Weights: Unresolved 50%, No Risk 20%, Fixed 30%
                b_status = random.choices([0, 1, 2], weights=[0.5, 0.2, 0.3])[0]
                
                branch = ComplianceBranch.objects.create(
                    record=record,
                    branch_name=b_name,
                    status=b_status,
                    remark="Auto generated mock data" if b_status != 0 else ""
                )
                record_branches.append(branch)
                branches_count += 1
                
            # Update Record Status based on branches
            # If any branch is 0 (Unresolved) -> Record is 0
            # If all branches are 1 (No Risk) -> Record is 1
            # Otherwise (all Fixed, or Mixed Fixed/No Risk) -> Record is 2 (Fixed)
            
            if any(b.status == 0 for b in record_branches):
                record.status = 0
            elif all(b.status == 1 for b in record_branches):
                record.status = 1
            else:
                record.status = 2
            record.save()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {records_count} compliance records and {branches_count} branches'))
