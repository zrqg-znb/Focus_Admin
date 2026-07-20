"""CMC 贡献看板 Django Ninja 接口。"""

from datetime import date

from ninja import Query, Router

from . import services
from .schemas import CmcPersonPageOut, CmcSummaryOut, CmcSyncRunIn, CmcSyncTaskOut

router = Router()


@router.get("/dashboard/summary", response=CmcSummaryOut, summary="CMC贡献看板汇总")
def get_cmc_summary(request, startDate: date = Query(...), endDate: date = Query(...)):
    """按日期范围读取本地 CMC 快照汇总指标。"""
    return services.get_summary(startDate, endDate)


@router.get("/persons", response=CmcPersonPageOut, summary="CMC贡献人员汇总表")
def list_cmc_persons(request, startDate: date = Query(...), endDate: date = Query(...), page: int = Query(1), pageSize: int = Query(20), userKeyword: str = Query("")):
    """按人员分页查看日期范围内的 CMC 贡献数据。"""
    return services.list_persons(startDate, endDate, page, pageSize, userKeyword)


@router.post("/sync-tasks", response=CmcSyncTaskOut, summary="手动同步CMC贡献数据")
def create_cmc_sync_task(request, payload: CmcSyncRunIn):
    """仅管理员可提交最多 31 天的 CMC 数据补数任务。"""
    return services.create_manual_task(request.auth, payload.startDate, payload.endDate)


@router.get("/sync-tasks/{task_id}", response=CmcSyncTaskOut, summary="CMC同步任务详情")
def get_cmc_sync_task(request, task_id: str):
    """返回 CMC 同步任务的执行状态和统计信息。"""
    return services.get_task(task_id)
