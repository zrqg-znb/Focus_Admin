from typing import List, Optional
from ninja import Router
from ninja.pagination import paginate
from common.fu_pagination import MyPagination
from common.fu_auth import BearerAuth as GlobalAuth
from apps.project_manager.models.sync_log_model import SyncLog
from ninja import Schema
from datetime import datetime

router = Router(tags=["Sync Log"], auth=GlobalAuth())

class SyncLogOut(Schema):
    id: str
    project_id: str
    sync_type: str
    sync_type_display: Optional[str] = None
    status: str
    result_summary: Optional[str] = None
    detail_log: Optional[str] = None
    duration: float
    sys_create_datetime: datetime
    creator_name: Optional[str] = None
    
    @staticmethod
    def resolve_sync_type_display(obj):
        return obj.get_sync_type_display()
        
    @staticmethod
    def resolve_creator_name(obj):
        return obj.sys_creator.name if obj.sys_creator else "System"

@router.get("/sync-logs", response=List[SyncLogOut], summary="获取同步日志列表")
@paginate(MyPagination)
def list_sync_logs(request):
    return SyncLog.objects.filter(sys_creator=request.auth).select_related('sys_creator').order_by('-sys_create_datetime')
