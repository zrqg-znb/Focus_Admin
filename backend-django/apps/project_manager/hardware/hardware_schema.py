from ninja import Field, ModelSchema, Schema
from typing import List, Optional

from .hardware_model import (
    CdcPlatform,
    HardwarePoint,
    IdvpPlatform,
    SmartScreenVersion,
    ViuPlatform,
)


class HardwarePointIn(Schema):
    code: str = Field(..., description="硬件点位")
    boards: List[str] = Field(default_factory=list, description="板子列表")
    remark: Optional[str] = Field(None, description="备注")


class HardwarePointUpdate(Schema):
    code: Optional[str] = None
    boards: Optional[List[str]] = None
    remark: Optional[str] = None


class HardwarePointOut(ModelSchema):
    class Meta:
        model = HardwarePoint
        fields = "__all__"


class PlatformConfigIn(Schema):
    name: str = Field(..., description="配置名称")
    remark: Optional[str] = Field(None, description="备注")


class PlatformConfigUpdate(Schema):
    name: Optional[str] = None
    remark: Optional[str] = None


class CdcPlatformOut(ModelSchema):
    class Meta:
        model = CdcPlatform
        fields = "__all__"


class ViuPlatformIn(Schema):
    name: str = Field(..., description="VIU硬件平台名称")
    configs: List[str] = Field(default_factory=list, description="典配列表")
    remark: Optional[str] = Field(None, description="备注")


class ViuPlatformUpdate(Schema):
    name: Optional[str] = None
    configs: Optional[List[str]] = None
    remark: Optional[str] = None


class ViuPlatformOut(ModelSchema):
    class Meta:
        model = ViuPlatform
        fields = "__all__"


class IdvpPlatformOut(ModelSchema):
    class Meta:
        model = IdvpPlatform
        fields = "__all__"


class SmartScreenVersionOut(ModelSchema):
    class Meta:
        model = SmartScreenVersion
        fields = "__all__"


class HardwareConfigOptionsOut(Schema):
    points: List[HardwarePointOut]
    viu_platforms: List[ViuPlatformOut]
    idvp_platforms: List[IdvpPlatformOut]
    cdc_platforms: List[CdcPlatformOut]
    smart_screen_versions: List[SmartScreenVersionOut]
