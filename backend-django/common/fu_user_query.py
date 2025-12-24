from core.dept.dept_model import Dept
from core.user.user_model import User
from core.user.user_schema import UserSchemaGetNameIn


def get_manager_list(data: UserSchemaGetNameIn):
    """
    获取用户上级列表
    注意：由于 manager 字段已改为存储静态字符串（姓名），不再关联 User 表，
    因此只能获取直属上级姓名，无法获取上级的 ID 或更深层级的上级。
    """
    users = User.objects.filter(id__in=data.ids).values('id', 'manager')
    
    result = []
    for user in users:
        result.append({
            "manager_id": None,
            "manager_name": user['manager']
        })
        
    if int(data.until) == 1:
        return result
    else:
        return [result]


def get_dept_lead_list1(data: UserSchemaGetNameIn):
    """
    获取部门领导列表
    注意：Dept 模型已移除 lead 字段，此功能不再可用
    """
    return []


def get_dept_lead_list(data: UserSchemaGetNameIn):
    """
    获取部门领导列表
    注意：Dept 模型已移除 lead 字段，此功能不再可用
    """
    return []
