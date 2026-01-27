from django.db.models import Count, Q
from .models import ComplianceRecord, ComplianceBranch
from core.user.user_model import User
from core.post.post_model import Post
from datetime import datetime, date

def get_post_stats():
    """
    获取岗位维度的合规风险统计，包括总览摘要
    """
    records = ComplianceRecord.objects.select_related('user').prefetch_related('user__post', 'branches').all()
    
    # Global counters
    total_risks = 0 # ChangeId count
    unresolved_risks = 0 # Unresolved ChangeId count
    total_branch_risks = 0 # Branch count
    unresolved_branch_risks = 0 # Unresolved Branch count
    
    all_users = set()
    
    post_stats = {}
    
    for record in records:
        # ChangeId counters
        total_risks += 1
        
        branches = record.branches.all()
        
        # Branch counters for this record
        r_total_branches = len(branches)
        r_unresolved_branches = sum(1 for b in branches if b.status == 0)
        
        # Global accumulation
        total_branch_risks += r_total_branches
        unresolved_branch_risks += r_unresolved_branches
        
        # Determine record status (Unresolved if any branch is unresolved)
        # Note: We rely on the record.status field which should be kept in sync, 
        # but let's calculate dynamically to be safe or use the field.
        # Using the logic: if any branch is 0, record is 0.
        is_unresolved_record = False
        if branches:
             if any(b.status == 0 for b in branches):
                is_unresolved_record = True
        else:
            if record.status == 0:
                is_unresolved_record = True
                
        if is_unresolved_record:
            unresolved_risks += 1
            
        user = record.user
        if user:
            all_users.add(user.id)
            posts = user.post.all()
        else:
            all_users.add("unknown")
            posts = []
            
        if not posts:
            posts_list = [{'id': "unknown", 'name': "未知岗位"}]
        else:
            posts_list = posts
            
        for post in posts_list:
            if isinstance(post, dict):
                p_id = post['id']
                p_name = post['name']
            else:
                p_id = str(post.id)
                p_name = post.name
                
            if p_id not in post_stats:
                post_stats[p_id] = {
                    "post_id": p_id,
                    "post_name": p_name,
                    "users": set(),
                    "total_risk_count": 0,
                    "unresolved_count": 0,
                    "total_branch_count": 0,
                    "unresolved_branch_count": 0
                }
            
            post_stats[p_id]["users"].add(user.id if user else "unknown")
            post_stats[p_id]["total_risk_count"] += 1
            if is_unresolved_record:
                post_stats[p_id]["unresolved_count"] += 1
            
            post_stats[p_id]["total_branch_count"] += r_total_branches
            post_stats[p_id]["unresolved_branch_count"] += r_unresolved_branches
            
    items = []
    for stat in post_stats.values():
        items.append({
            "post_id": stat["post_id"],
            "post_name": stat["post_name"],
            "user_count": len(stat["users"]),
            "total_risk_count": stat["total_risk_count"],
            "unresolved_count": stat["unresolved_count"],
            "total_branch_count": stat["total_branch_count"],
            "unresolved_branch_count": stat["unresolved_branch_count"]
        })
        
    return {
        "total_risks": total_risks,
        "unresolved_risks": unresolved_risks,
        "total_branch_risks": total_branch_risks,
        "unresolved_branch_risks": unresolved_branch_risks,
        "affected_users": len(all_users),
        "items": items
    }

def get_post_users_detail(post_id: str, start_date: str = None, end_date: str = None):
    """
    获取指定岗位下用户的合规风险详情，支持时间筛选
    """
    if post_id == "unknown" or not post_id:
        users = User.objects.filter(post__isnull=True)
    else:
        users = User.objects.filter(post__id=post_id)
        
    user_ids = users.values_list('id', flat=True)
    
    records = ComplianceRecord.objects.filter(user_id__in=user_ids).prefetch_related('branches', 'user', 'user__post')
    
    if start_date:
        records = records.filter(update_time__gte=start_date)
    if end_date:
        records = records.filter(update_time__lte=end_date)
    
    user_stats = {}
    
    summary = {
        "total_risks": 0,
        "unresolved_risks": 0,
        "fixed_risks": 0,
        "no_risk_risks": 0,
        "total_branch_risks": 0,
        "unresolved_branch_risks": 0,
        "fixed_branch_risks": 0,
        "no_risk_branch_risks": 0
    }
    
    for record in records:
        branches = record.branches.all()
        
        # Branch counters
        r_total_branches = len(branches)
        r_unresolved_branches = sum(1 for b in branches if b.status == 0)
        r_fixed_branches = sum(1 for b in branches if b.status == 2)
        r_no_risk_branches = sum(1 for b in branches if b.status == 1)
        
        # Global Summary Accumulation (Branch)
        summary["total_branch_risks"] += r_total_branches
        summary["unresolved_branch_risks"] += r_unresolved_branches
        summary["fixed_branch_risks"] += r_fixed_branches
        summary["no_risk_branch_risks"] += r_no_risk_branches

        # Record Status Logic
        status = record.status
        if branches:
            if any(b.status == 0 for b in branches):
                status = 0
            elif all(b.status == 1 for b in branches):
                status = 1
            elif all(b.status == 2 for b in branches):
                status = 2
            else:
                status = 2 # Mixed fixed/no-risk -> Fixed/Resolved
        
        # Global Summary Accumulation (Record)
        summary["total_risks"] += 1
        if status == 0:
            summary["unresolved_risks"] += 1
        elif status == 1:
            summary["no_risk_risks"] += 1
        elif status == 2:
            summary["fixed_risks"] += 1
            
        u_id = str(record.user.id)
        if u_id not in user_stats:
            post_names = [p.name for p in record.user.post.all()]
            post_name_str = ", ".join(post_names) if post_names else "未知岗位"
            
            user_stats[u_id] = {
                "user_id": u_id,
                "user_name": record.user.name or record.user.username,
                "avatar": record.user.avatar,
                "post_name": post_name_str,
                "total_count": 0,
                "unresolved_count": 0,
                "fixed_count": 0,
                "no_risk_count": 0,
                "total_branch_count": 0,
                "unresolved_branch_count": 0,
                "fixed_branch_count": 0,
                "no_risk_branch_count": 0
            }
            
        # User Stats Accumulation (Record)
        user_stats[u_id]["total_count"] += 1
        if status == 0:
            user_stats[u_id]["unresolved_count"] += 1
        elif status == 1:
            user_stats[u_id]["no_risk_count"] += 1
        elif status == 2:
            user_stats[u_id]["fixed_count"] += 1
            
        # User Stats Accumulation (Branch)
        user_stats[u_id]["total_branch_count"] += r_total_branches
        user_stats[u_id]["unresolved_branch_count"] += r_unresolved_branches
        user_stats[u_id]["fixed_branch_count"] += r_fixed_branches
        user_stats[u_id]["no_risk_branch_count"] += r_no_risk_branches
            
    return {
        **summary,
        "items": list(user_stats.values())
    }

def get_user_records(user_id: str):
    """
    获取用户的详细风险记录
    """
    return ComplianceRecord.objects.filter(user_id=user_id).prefetch_related('branches').order_by('status', '-update_time')

def update_branch_status(branch_id: str, status: int, remark: str = None, user: User = None):
    """
    更新分支状态
    """
    branch = ComplianceBranch.objects.get(id=branch_id)
    branch.status = status
    
    if remark:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = user.name or user.username if user else "System"
        
        status_label = {0: '待处理', 1: '无风险', 2: '已修复'}.get(status, '未知')
        
        log_entry = f"[{current_time}] {username}: 将状态更新为【{status_label}】，备注：{remark}"
        
        if branch.remark:
            branch.remark = f"{branch.remark}\n{log_entry}"
        else:
            branch.remark = log_entry
            
    branch.save()
    
    # Update parent record status
    record = branch.record
    all_branches = record.branches.all()
    
    if any(b.status == 0 for b in all_branches):
        record.status = 0
    elif all(b.status == 1 for b in all_branches):
        record.status = 1
    else:
        record.status = 2
        
    record.save()
    
    return branch
