from typing import List

from django.db import IntegrityError
from ninja import Router
from ninja.errors import HttpError

from common import fu_crud
from common.fu_auth import BearerAuth as GlobalAuth
from .hardware_model import (
    CdcPlatform,
    HardwarePoint,
    SmartScreenVersion,
    ViuPlatform,
)
from .hardware_schema import (
    CdcPlatformOut,
    HardwareConfigOptionsOut,
    HardwarePointIn,
    HardwarePointOut,
    HardwarePointUpdate,
    PlatformConfigIn,
    PlatformConfigUpdate,
    SmartScreenVersionOut,
    ViuPlatformOut,
)

router = Router(tags=["HardwareConfig"], auth=GlobalAuth())


def _normalize_point_code(code: str | None) -> str:
    return (code or "").strip()


def _ensure_point_code_unique(code: str, exclude_id: str | None = None):
    if not code:
        return
    queryset = HardwarePoint.objects.filter(code=code)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    if queryset.exists():
        raise HttpError(409, f"硬件点位已存在: {code}")


@router.get("/options", response=HardwareConfigOptionsOut, summary="获取典配配置项")
def list_options(request):
    return {
        "points": HardwarePoint.objects.filter(is_deleted=False).order_by(
            "-sort", "-sys_create_datetime"
        ),
        "viu_platforms": ViuPlatform.objects.filter(is_deleted=False).order_by(
            "-sort", "-sys_create_datetime"
        ),
        "cdc_platforms": CdcPlatform.objects.filter(is_deleted=False).order_by(
            "-sort", "-sys_create_datetime"
        ),
        "smart_screen_versions": SmartScreenVersion.objects.filter(
            is_deleted=False
        ).order_by("-sort", "-sys_create_datetime"),
    }


@router.get("/points", response=List[HardwarePointOut], summary="获取硬件点位列表")
def list_points(request):
    return HardwarePoint.objects.filter(is_deleted=False).order_by(
        "-sort", "-sys_create_datetime"
    )


@router.post("/points", response=HardwarePointOut, summary="创建硬件点位")
def create_point(request, data: HardwarePointIn):
    payload = data.dict()
    payload["code"] = _normalize_point_code(payload.get("code"))
    _ensure_point_code_unique(payload["code"])
    try:
        return fu_crud.create(request, payload, HardwarePoint)
    except IntegrityError as error:
        if "pm_hardware_point.code" in str(error) or "code" in str(error):
            raise HttpError(409, f"硬件点位已存在: {payload['code']}")
        raise error


@router.put("/points/{point_id}", response=HardwarePointOut, summary="更新硬件点位")
def update_point(request, point_id: str, data: HardwarePointUpdate):
    payload = data.dict(exclude_none=True)
    if "code" in payload:
        payload["code"] = _normalize_point_code(payload.get("code"))
        _ensure_point_code_unique(payload["code"], exclude_id=point_id)
    try:
        return fu_crud.update(request, point_id, payload, HardwarePoint)
    except IntegrityError as error:
        if "pm_hardware_point.code" in str(error) or "code" in str(error):
            conflict_code = payload.get("code") or ""
            raise HttpError(409, f"硬件点位已存在: {conflict_code}")
        raise error


@router.delete("/points/{point_id}", response=HardwarePointOut, summary="删除硬件点位")
def delete_point(request, point_id: str):
    return fu_crud.delete(point_id, HardwarePoint)


@router.get("/cdc-platforms", response=List[CdcPlatformOut], summary="获取CDC平台列表")
def list_cdc_platforms(request):
    return CdcPlatform.objects.filter(is_deleted=False).order_by(
        "-sort", "-sys_create_datetime"
    )


@router.get("/viu-platforms", response=List[ViuPlatformOut], summary="获取VIU平台列表")
def list_viu_platforms(request):
    return ViuPlatform.objects.filter(is_deleted=False).order_by(
        "-sort", "-sys_create_datetime"
    )


@router.post("/viu-platforms", response=ViuPlatformOut, summary="创建VIU平台")
def create_viu_platform(request, data: PlatformConfigIn):
    return fu_crud.create(request, data, ViuPlatform)


@router.put("/viu-platforms/{platform_id}", response=ViuPlatformOut, summary="更新VIU平台")
def update_viu_platform(request, platform_id: str, data: PlatformConfigUpdate):
    return fu_crud.update(request, platform_id, data, ViuPlatform)


@router.delete("/viu-platforms/{platform_id}", response=ViuPlatformOut, summary="删除VIU平台")
def delete_viu_platform(request, platform_id: str):
    return fu_crud.delete(platform_id, ViuPlatform)


@router.post("/cdc-platforms", response=CdcPlatformOut, summary="创建CDC平台")
def create_cdc_platform(request, data: PlatformConfigIn):
    return fu_crud.create(request, data, CdcPlatform)


@router.put("/cdc-platforms/{platform_id}", response=CdcPlatformOut, summary="更新CDC平台")
def update_cdc_platform(request, platform_id: str, data: PlatformConfigUpdate):
    return fu_crud.update(request, platform_id, data, CdcPlatform)


@router.delete("/cdc-platforms/{platform_id}", response=CdcPlatformOut, summary="删除CDC平台")
def delete_cdc_platform(request, platform_id: str):
    return fu_crud.delete(platform_id, CdcPlatform)


@router.get(
    "/smart-screen-versions",
    response=List[SmartScreenVersionOut],
    summary="获取智慧屏版本列表",
)
def list_smart_screen_versions(request):
    return SmartScreenVersion.objects.filter(is_deleted=False).order_by(
        "-sort", "-sys_create_datetime"
    )


@router.post(
    "/smart-screen-versions",
    response=SmartScreenVersionOut,
    summary="创建智慧屏版本",
)
def create_smart_screen_version(request, data: PlatformConfigIn):
    return fu_crud.create(request, data, SmartScreenVersion)


@router.put(
    "/smart-screen-versions/{version_id}",
    response=SmartScreenVersionOut,
    summary="更新智慧屏版本",
)
def update_smart_screen_version(request, version_id: str, data: PlatformConfigUpdate):
    return fu_crud.update(request, version_id, data, SmartScreenVersion)


@router.delete(
    "/smart-screen-versions/{version_id}",
    response=SmartScreenVersionOut,
    summary="删除智慧屏版本",
)
def delete_smart_screen_version(request, version_id: str):
    return fu_crud.delete(version_id, SmartScreenVersion)
