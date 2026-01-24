from django.db.models import Count, Q
from .models import ComplianceRecord
from core.user.user_model import User
from core.dept.dept_model import Dept

def get_department_stats():
    """
    获取部门维度的合规风险统计
    """
    # 获取所有有风险记录的用户及其部门
    records = ComplianceRecord.objects.select_related('user', 'user__dept').all()
    
    dept_stats = {}
    
    for record in records:
        user = record.user
        if not user or not user.dept:
            dept_key = "unknown"
            dept_name = "未知部门"
            dept_id = ""
        else:
            dept_key = user.dept.id
            dept_name = user.dept.name
            dept_id = user.dept.id
            
        if dept_key not in dept_stats:
            dept_stats[dept_key] = {
                "dept_id": dept_id,
                "dept_name": dept_name,
                "users": set(),
                "total_risk_count": 0,
                "unresolved_count": 0
            }
            
        dept_stats[dept_key]["users"].add(user.id)
        dept_stats[dept_key]["total_risk_count"] += 1
        if record.status == 0:
            dept_stats[dept_key]["unresolved_count"] += 1
            
    result = []
    for stat in dept_stats.values():
        result.append({
            "dept_id": stat["dept_id"],
            "dept_name": stat["dept_name"],
            "user_count": len(stat["users"]),
            "total_risk_count": stat["total_risk_count"],
            "unresolved_count": stat["unresolved_count"]
        })
        
    return result

def get_department_users_detail(dept_id: str):
    """
    获取指定部门下用户的合规风险详情
    """
    # 过滤该部门下的用户
    if dept_id == "unknown" or not dept_id:
        users = User.objects.filter(dept__isnull=True)
    else:
        users = User.objects.filter(dept_id=dept_id)
        
    user_ids = users.values_list('id', flat=True)
    
    # 获取这些用户的风险记录
    records = ComplianceRecord.objects.filter(user_id__in=user_ids)
    
    user_stats = {}
    
    for record in records:
        u_id = record.user_id
        if u_id not in user_stats:
            user_stats[u_id] = {
                "user_id": u_id,
                "user_name": record.user.name or record.user.username,
                "avatar": record.user.avatar,
                "dept_name": record.user.dept.name if record.user.dept else "未知部门",
                "total_count": 0,
                "unresolved_count": 0,
                "fixed_count": 0,
                "no_risk_count": 0
            }
            
        user_stats[u_id]["total_count"] += 1
        if record.status == 0:
            user_stats[u_id]["unresolved_count"] += 1
        elif record.status == 1:
            user_stats[u_id]["no_risk_count"] += 1
        elif record.status == 2:
            user_stats[u_id]["fixed_count"] += 1
            
    return list(user_stats.values())

def get_user_records(user_id: str):
    """
    获取用户的详细风险记录
    """
    return ComplianceRecord.objects.filter(user_id=user_id).order_by('status', '-update_time')

def update_record_status(record_id: str, status: int, remark: str = None):
    """
    更新风险记录状态
    """
    record = ComplianceRecord.objects.get(id=record_id)
    record.status = status
    if remark is not None:
        record.remark = remark
    record.save()
    return record
