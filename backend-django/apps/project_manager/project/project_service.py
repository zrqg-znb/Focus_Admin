from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from common import fu_crud

from apps.project_manager.dts.dts_service import sync_project_dts
from apps.project_manager.hardware.hardware_model import (
    CdcPlatform,
    HardwarePoint,
    IdvpPlatform,
    SmartScreenVersion,
    ViuPlatform,
)
from apps.project_manager.iteration.iteration_sync import sync_project_iterations
from apps.project_manager.milestone.milestone_model import Milestone
from .project_model import (
    PHASE_SCENARIO_COCKPIT,
    PHASE_SCENARIO_VEHICLE,
    Project,
    ProjectPhaseConfig,
)
from .project_schema import ProjectCreateSchema, ProjectUpdateSchema


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_id_list(raw_values) -> list[str]:
    if raw_values is None:
        return []
    values = raw_values if isinstance(raw_values, list) else [raw_values]
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_requirement_source_config(
    design_id: str | None,
    sub_teams,
) -> tuple[str | None, list[str]]:
    return _normalize_optional_text(design_id), _normalize_id_list(sub_teams)


def _normalize_iteration_quality_config(
    *,
    enable_iteration: bool,
    enable_iteration_quality_metrics: bool,
    iteration_quality_oem_name: str | None,
    iteration_quality_module: str | None,
) -> tuple[bool, str | None, str | None]:
    if not enable_iteration:
        return False, None, None

    if not enable_iteration_quality_metrics:
        return False, None, None

    normalized_oem_name = _normalize_optional_text(iteration_quality_oem_name)
    normalized_module = _normalize_optional_text(iteration_quality_module)

    if not normalized_oem_name or not normalized_module:
        raise HttpError(
            422,
            "开启健康迭代代码质量出口指标后，OEMName和模块名不能为空",
        )

    return True, normalized_oem_name, normalized_module


def _resolve_phase_scenario(domain: str) -> str:
    if "座舱" in (domain or ""):
        return PHASE_SCENARIO_COCKPIT
    if "车控" in (domain or ""):
        return PHASE_SCENARIO_VEHICLE
    raise HttpError(422, "项目领域仅支持车控项目或座舱项目")


def _build_phase_config_rows(
    project: Project,
    phase_configs: list[dict],
) -> list[tuple[ProjectPhaseConfig, list[SmartScreenVersion]]]:
    scenario = _resolve_phase_scenario(project.domain)
    stage_names = set()
    rows: list[tuple[ProjectPhaseConfig, list[SmartScreenVersion]]] = []

    hardware_points = {}
    cdc_platforms = {}
    smart_versions = {}
    viu_platform_configs = {}
    if scenario == PHASE_SCENARIO_VEHICLE:
        hardware_points = {
            point.code: point
            for point in HardwarePoint.objects.filter(is_deleted=False)
        }
        viu_platform_configs = {
            item.name: set(item.configs or [])
            for item in ViuPlatform.objects.filter(is_deleted=False)
        }
    else:
        cdc_platforms = {
            str(item.id): item
            for item in CdcPlatform.objects.filter(is_deleted=False)
        }
        smart_versions = {
            str(item.id): item
            for item in SmartScreenVersion.objects.filter(is_deleted=False)
        }
        if len(phase_configs) != 1:
            raise HttpError(422, "座舱项目仅允许配置一个配套版本")

    for item in phase_configs:
        stage_name = (item.get("stage_name") or "").strip()
        if scenario == PHASE_SCENARIO_COCKPIT:
            stage_name = "座舱配套版本"
        if not stage_name:
            raise HttpError(422, "阶段名称不能为空")
        if stage_name in stage_names:
            raise HttpError(422, f"阶段名称重复: {stage_name}")
        stage_names.add(stage_name)

        stage_start = item.get("stage_start")
        stage_end = item.get("stage_end")
        if scenario == PHASE_SCENARIO_COCKPIT:
            stage_start = None
            stage_end = None
        if stage_start and stage_end and stage_start > stage_end:
            raise HttpError(422, f"阶段 {stage_name} 的开始日期不能晚于结束日期")

        if scenario == PHASE_SCENARIO_VEHICLE:
            hardware_items = item.get("vehicle_hardware") or []
            if not hardware_items:
                raise HttpError(422, f"阶段 {stage_name} 需要配置车控硬件组合")

            normalized_hardware = []
            for hardware in hardware_items:
                point = (hardware.get("point") or "").strip()
                board = (hardware.get("board") or "").strip()
                config_type = (hardware.get("config_type") or "").strip()
                bomid = (hardware.get("bomid") or "").strip()
                if not point or not board or not config_type or not bomid:
                    raise HttpError(422, f"阶段 {stage_name} 的硬件组合不完整")

                point_obj = hardware_points.get(point)
                if not point_obj:
                    raise HttpError(422, f"阶段 {stage_name} 使用了不存在的点位: {point}")
                if point_obj.boards and board not in point_obj.boards:
                    raise HttpError(
                        422,
                        f"阶段 {stage_name} 的板子 {board} 不在点位 {point} 可选列表中",
                    )
                board_config_types = viu_platform_configs.get(board)
                if board_config_types is None:
                    raise HttpError(
                        422,
                        f"阶段 {stage_name} 的板子 {board} 未在VIU硬件平台配置中维护",
                    )
                if not board_config_types:
                    raise HttpError(
                        422,
                        f"阶段 {stage_name} 的板子 {board} 尚未配置典配类型",
                    )
                if config_type not in board_config_types:
                    raise HttpError(
                        422,
                        f"阶段 {stage_name} 的板子 {board} 不支持典配类型: {config_type}",
                    )
                normalized_hardware.append(
                    {
                        "point": point,
                        "board": board,
                        "config_type": config_type,
                        "bomid": bomid,
                    }
                )

            rows.append(
                (
                    ProjectPhaseConfig(
                        project=project,
                        stage_name=stage_name,
                        stage_start=stage_start,
                        stage_end=stage_end,
                        scenario=scenario,
                        vehicle_hardware=normalized_hardware,
                    ),
                    [],
                )
            )
        else:
            cdc_platform_id = str(item.get("cdc_platform_id") or "").strip()
            smart_screen_version_ids = _normalize_id_list(
                item.get("smart_screen_version_ids"),
            )
            if not smart_screen_version_ids:
                legacy_smart_screen_version_id = str(
                    item.get("smart_screen_version_id") or ""
                ).strip()
                if legacy_smart_screen_version_id:
                    smart_screen_version_ids = [legacy_smart_screen_version_id]

            if not cdc_platform_id and len(smart_screen_version_ids) == 0:
                raise HttpError(
                    422,
                    f"阶段 {stage_name} 至少需要配置CDC平台或智慧屏版本",
                )

            cdc_platform = None
            if cdc_platform_id:
                cdc_platform = cdc_platforms.get(cdc_platform_id)
                if not cdc_platform:
                    raise HttpError(422, f"阶段 {stage_name} 的CDC平台不存在")

            smart_versions_in_phase = []
            for smart_screen_version_id in smart_screen_version_ids:
                smart_version = smart_versions.get(smart_screen_version_id)
                if not smart_version:
                    raise HttpError(422, f"阶段 {stage_name} 的智慧屏版本不存在")
                smart_versions_in_phase.append(smart_version)

            rows.append(
                (
                    ProjectPhaseConfig(
                        project=project,
                        stage_name=stage_name,
                        stage_start=stage_start,
                        stage_end=stage_end,
                        scenario=scenario,
                        vehicle_hardware=[],
                        cdc_platform=cdc_platform,
                    ),
                    smart_versions_in_phase,
                )
            )

    return rows


def _sync_phase_configs(
    project: Project,
    phase_configs: list[dict] | None,
    *,
    require_when_enabled: bool,
):
    if not project.enable_hardware_config:
        project.phase_configs.all().delete()
        if project.viu_platform_id or project.idvp_platform_id:
            project.viu_platform = None
            project.idvp_platform = None
            project.save(update_fields=["viu_platform", "idvp_platform"])
        return

    scenario = _resolve_phase_scenario(project.domain)
    if scenario == PHASE_SCENARIO_VEHICLE:
        if not project.idvp_platform_id:
            raise HttpError(422, "车控项目开启典配后必须选择IDVP平台")
        if not IdvpPlatform.objects.filter(
            id=project.idvp_platform_id,
            is_deleted=False,
        ).exists():
            raise HttpError(422, "选择的IDVP平台不存在")
    elif project.viu_platform_id or project.idvp_platform_id:
        project.viu_platform = None
        project.idvp_platform = None
        project.save(update_fields=["viu_platform", "idvp_platform"])

    if phase_configs is None:
        if require_when_enabled:
            raise HttpError(
                422,
                "开启典配后必须配置配套版本"
                if scenario == PHASE_SCENARIO_COCKPIT
                else "开启典配后必须至少配置一个阶段",
            )
        if project.phase_configs.exclude(scenario=scenario).exists():
            raise HttpError(422, "项目领域已变更，请重新配置阶段典配")
        return

    if len(phase_configs) == 0:
        raise HttpError(
            422,
            "开启典配后必须配置配套版本"
            if scenario == PHASE_SCENARIO_COCKPIT
            else "开启典配后必须至少配置一个阶段",
        )

    rows = _build_phase_config_rows(project, phase_configs)
    project.phase_configs.all().delete()
    for row, smart_versions in rows:
        row.save()
        if smart_versions:
            row.smart_screen_versions.set(smart_versions)


@transaction.atomic
def create_project(request, data: ProjectCreateSchema):
    try:
        data_dict = data.dict()
        manager_ids = data_dict.pop("manager_ids", [])
        phase_configs = data_dict.pop("phase_configs", None)
        normalized_quality_switch, normalized_quality_oem_name, normalized_quality_module = (
            _normalize_iteration_quality_config(
                enable_iteration=bool(data_dict.get("enable_iteration", True)),
                enable_iteration_quality_metrics=bool(
                    data_dict.get("enable_iteration_quality_metrics", False)
                ),
                iteration_quality_oem_name=data_dict.get("iteration_quality_oem_name"),
                iteration_quality_module=data_dict.get("iteration_quality_module"),
            )
        )
        normalized_design_id, normalized_sub_teams = _normalize_requirement_source_config(
            data_dict.get("design_id"),
            data_dict.get("sub_teams"),
        )
        data_dict["version_c"] = _normalize_optional_text(data_dict.get("version_c"))
        data_dict["enable_iteration_quality_metrics"] = normalized_quality_switch
        data_dict["iteration_quality_oem_name"] = normalized_quality_oem_name
        data_dict["iteration_quality_module"] = normalized_quality_module
        data_dict["design_id"] = normalized_design_id
        data_dict["sub_teams"] = normalized_sub_teams

        project = fu_crud.create(request, data_dict, Project)

        if manager_ids:
            project.managers.set(manager_ids)

        _sync_phase_configs(
            project,
            phase_configs,
            require_when_enabled=True,
        )

        if project.enable_milestone:
            Milestone.objects.create(project=project)

        if project.enable_iteration and project.design_id and project.sub_teams:
            sync_project_iterations(project)

        if project.enable_dts and project.ws_id and project.di_teams:
            sync_project_dts(project)

        return project
    except IntegrityError as e:
        if "code" in str(e):
            raise HttpError(422, "项目编码已存在")
        raise e


@transaction.atomic
def update_project(request, id: str, data: ProjectUpdateSchema):
    project = get_object_or_404(Project, id=id)
    old_enable_milestone = project.enable_milestone
    old_enable_hardware_config = project.enable_hardware_config
    old_design_id = project.design_id
    old_sub_teams = project.sub_teams
    old_ws_id = project.ws_id
    old_di_teams = project.di_teams

    phase_configs_sentinel = object()
    data_dict = data.dict(exclude_unset=True)
    manager_ids = data_dict.pop("manager_ids", None)
    phase_configs = data_dict.pop("phase_configs", phase_configs_sentinel)
    enable_iteration = bool(data_dict.get("enable_iteration", project.enable_iteration))
    enable_iteration_quality_metrics = bool(
        data_dict.get(
            "enable_iteration_quality_metrics",
            project.enable_iteration_quality_metrics,
        )
    )
    iteration_quality_oem_name = data_dict.get(
        "iteration_quality_oem_name",
        project.iteration_quality_oem_name,
    )
    iteration_quality_module = data_dict.get(
        "iteration_quality_module",
        project.iteration_quality_module,
    )
    normalized_design_id, normalized_sub_teams = _normalize_requirement_source_config(
        data_dict.get("design_id", project.design_id),
        data_dict.get("sub_teams", project.sub_teams),
    )
    if "version_c" in data_dict:
        data_dict["version_c"] = _normalize_optional_text(data_dict.get("version_c"))
    normalized_quality_switch, normalized_quality_oem_name, normalized_quality_module = (
        _normalize_iteration_quality_config(
            enable_iteration=enable_iteration,
            enable_iteration_quality_metrics=enable_iteration_quality_metrics,
            iteration_quality_oem_name=iteration_quality_oem_name,
            iteration_quality_module=iteration_quality_module,
        )
    )
    data_dict["enable_iteration_quality_metrics"] = normalized_quality_switch
    data_dict["iteration_quality_oem_name"] = normalized_quality_oem_name
    data_dict["iteration_quality_module"] = normalized_quality_module
    data_dict["design_id"] = normalized_design_id
    data_dict["sub_teams"] = normalized_sub_teams

    project = fu_crud.update(request, id, data_dict, Project)

    if manager_ids is not None:
        project.managers.set(manager_ids)

    _sync_phase_configs(
        project,
        None if phase_configs is phase_configs_sentinel else phase_configs,
        require_when_enabled=(
            project.enable_hardware_config and not old_enable_hardware_config
        ),
    )

    if project.enable_milestone and not old_enable_milestone:
        if not hasattr(project, "milestone"):
            Milestone.objects.create(project=project)

    if project.enable_iteration:
        config_changed = (
            project.design_id != old_design_id
            or project.sub_teams != old_sub_teams
        )
        if (
            config_changed or not project.iterations.exists()
        ) and project.design_id and project.sub_teams:
            sync_project_iterations(project)

    if project.enable_dts:
        dts_config_changed = (
            project.ws_id != old_ws_id
            or project.di_teams != old_di_teams
        )
        if dts_config_changed or not project.dts_teams.exists():
            sync_project_dts(project)

    return project


def delete_project(request, id: str):
    return fu_crud.delete(id, Project)


def get_project(request, id: str):
    return get_object_or_404(
        Project.objects.select_related("viu_platform", "idvp_platform").prefetch_related(
            "managers",
            "phase_configs__cdc_platform",
            "phase_configs__smart_screen_versions",
        ),
        id=id,
    )


def favorite_project(request, id: str):
    project = get_object_or_404(Project, id=id)
    project.favorited_by.add(request.auth)
    return True


def unfavorite_project(request, id: str):
    project = get_object_or_404(Project, id=id)
    project.favorited_by.remove(request.auth)
    return True
