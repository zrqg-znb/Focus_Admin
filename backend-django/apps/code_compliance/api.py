from ninja import Router
from typing import List, Optional
from .schemas import ComplianceRecordSchema, ComplianceUpdateSchema, OverviewSummarySchema, DetailSummarySchema
from .services import get_department_stats, get_department_users_detail, get_user_records, update_record_status

router = Router()

@router.get("/stats/dept", response=OverviewSummarySchema)
def list_dept_stats(request):
    data = get_department_stats()
    return data

@router.get("/stats/dept/{dept_id}/users", response=DetailSummarySchema)
def list_dept_users(request, dept_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    data = get_department_users_detail(dept_id, start_date, end_date)
    return data

@router.get("/user/{user_id}/records", response=List[ComplianceRecordSchema])
def list_user_records(request, user_id: str):
    data = get_user_records(user_id)
    return data

@router.put("/record/{record_id}")
def update_record(request, record_id: str, data: ComplianceUpdateSchema):
    # Pass request.auth (User object) to service
    update_record_status(record_id, data.status, data.remark, user=request.auth)
    return {"msg": "操作成功"}
