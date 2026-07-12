from datetime import datetime
from typing import Optional

from ninja import File, Query, Router, UploadedFile

from . import contribution_services as services
from .contribution_schemas import (
    ContributionCategoryDistributionOut,
    ContributionCollectRunIn,
    ContributionCollectRunOut,
    ContributionCollectTaskOut,
    ContributionCodeBaselineIn,
    ContributionCodeBaselineOut,
    ContributionExportTaskIn,
    ContributionExportTaskOut,
    ContributionExportTaskPrepareOut,
    ContributionMetricOut,
    ContributionPersonRankingItemOut,
    ContributionRankingItemOut,
    ContributionRecordOut,
    ContributionTrendPointOut,
    PaginatedContributionCollectTaskOut,
    PaginatedContributionCodeBaselineOut,
    PaginatedContributionRecordOut,
)


router = Router()


def _filters(**kwargs) -> dict:
    """把贡献看板查询参数集中成服务层筛选字典。"""
    return {
        "organization_ids": kwargs.get("organization_ids"),
        "repository_ids": kwargs.get("repository_ids"),
        "branch_ids": kwargs.get("branch_ids"),
        "branch_type": kwargs.get("branch_type"),
        "repo_type": kwargs.get("repo_type"),
        "domain": kwargs.get("domain"),
        "pl_group_ids": kwargs.get("pl_group_ids"),
        "author_username": kwargs.get("author_username"),
        "keyword": kwargs.get("keyword"),
        "merged_after": kwargs.get("merged_after"),
        "merged_before": kwargs.get("merged_before"),
    }


@router.get("/dashboard/summary", response=ContributionMetricOut, summary="代码贡献核心指标")
def get_contribution_summary(
    request,
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pl_group_ids: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
):
    """查询代码贡献看板 8 项核心指标。"""
    return services.get_dashboard_summary(**_filters(**locals()))


@router.get("/dashboard/trend", response=list[ContributionTrendPointOut], summary="代码贡献日趋势")
def get_contribution_trend(
    request,
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pl_group_ids: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
):
    """查询新增、删除、总变更等日趋势。"""
    return services.get_dashboard_trend(**_filters(**locals()))


@router.get(
    "/dashboard/repository-ranking",
    response=list[ContributionRankingItemOut],
    summary="代码库分支贡献排行",
)
def get_contribution_repository_ranking(
    request,
    limit: int = Query(20),
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pl_group_ids: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
):
    """按代码库和分支维度查询贡献排行。"""
    return services.get_repository_ranking(limit=limit, **_filters(**locals()))


@router.get(
    "/dashboard/person-ranking",
    response=list[ContributionPersonRankingItemOut],
    summary="人员贡献排行",
)
def get_contribution_person_ranking(
    request,
    limit: int = Query(20),
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pl_group_ids: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
):
    """按 CR 创建人查询贡献排行。"""
    return services.get_person_ranking(limit=limit, **_filters(**locals()))


@router.get(
    "/dashboard/category-distribution",
    response=ContributionCategoryDistributionOut,
    summary="代码贡献类别分布",
)
def get_contribution_category_distribution(
    request,
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pl_group_ids: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
):
    """按仓库类型、领域、PL 组查询类别分布。"""
    return services.get_category_distribution(**_filters(**locals()))


@router.get("/records", response=PaginatedContributionRecordOut, summary="代码贡献CR明细")
def list_contribution_records(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pl_group_ids: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
):
    """分页查询贡献 CR 明细。"""
    return services.list_records(page=page, page_size=pageSize, **_filters(**locals()))


@router.get("/code-baselines", response=PaginatedContributionCodeBaselineOut, summary="代码量基线列表")
def list_contribution_code_baselines(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    current_only: bool = Query(True),
    organization_ids: Optional[str] = Query(None),
    repository_ids: Optional[str] = Query(None),
    branch_ids: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
):
    """分页查询代码量基线。"""
    return services.list_code_baselines(
        page=page,
        page_size=pageSize,
        current_only=current_only,
        **_filters(**locals()),
    )


@router.post("/code-baselines", response=ContributionCodeBaselineOut, summary="维护代码量基线")
def create_contribution_code_baseline(request, payload: ContributionCodeBaselineIn):
    """新增一次代码量基线覆盖校准。"""
    return services.save_code_baseline(request.auth, payload)


@router.get("/code-baselines/template", summary="下载代码量基线模板")
def download_contribution_code_baseline_template(request):
    """下载代码量基线导入模板。"""
    return services.build_baseline_template_response()


@router.post("/code-baselines/import", summary="导入代码量基线")
def import_contribution_code_baselines(request, file: UploadedFile = File(...)):
    """批量导入代码量基线。"""
    return services.import_code_baselines(request.auth, file)


@router.get("/collect-tasks", response=PaginatedContributionCollectTaskOut, summary="代码贡献采集任务")
def list_contribution_collect_tasks(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    status: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
):
    """分页查询贡献采集任务历史。"""
    return services.list_collect_tasks(page=page, page_size=pageSize, status=status, trigger_type=trigger_type)


@router.post("/collect-tasks/run", response=ContributionCollectRunOut, summary="手动触发代码贡献采集")
def run_contribution_collect_task(request, payload: ContributionCollectRunIn):
    """管理员手动提交一次代码贡献采集任务。"""
    return services.run_collect_task(request.auth, payload)


@router.get("/collect-tasks/{task_id}", response=ContributionCollectTaskOut, summary="代码贡献采集任务详情")
def get_contribution_collect_task(request, task_id: str):
    """查询单条贡献采集任务详情。"""
    return services.get_collect_task(task_id)


@router.post("/export-tasks", response=ContributionExportTaskPrepareOut, summary="创建代码贡献导出任务")
def prepare_contribution_export_task(request, payload: ContributionExportTaskIn):
    """创建代码贡献看板异步导出任务。"""
    return services.prepare_export_task(request.auth, payload)


@router.get("/export-tasks/{task_id}", response=ContributionExportTaskOut, summary="代码贡献导出任务详情")
def get_contribution_export_task(request, task_id: str):
    """查询当前用户的贡献导出任务。"""
    return services.get_export_task(request.auth, task_id)


@router.get("/export-tasks/{task_id}/download", summary="下载代码贡献导出文件")
def download_contribution_export_task(request, task_id: str):
    """下载当前用户已完成的贡献导出文件。"""
    return services.download_export_task_file(request.auth, task_id)
