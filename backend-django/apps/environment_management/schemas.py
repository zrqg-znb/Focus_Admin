from datetime import datetime
from typing import List, Optional

from ninja import Field, Schema


class DeviceTypeIn(Schema):
    parent_id: Optional[str] = None
    name: str
    sort: int = 0
    is_active: bool = True


class DeviceTypeOut(Schema):
    id: str
    parent_id: Optional[str] = None
    name: str
    sort: int = 0
    is_active: bool = True
    children: List['DeviceTypeOut'] = Field(default_factory=list)


class TestDeviceIn(Schema):
    device_type_id: str
    name: str
    sort: int = 0
    is_active: bool = True
    remark: str = ''


class TestDeviceOut(Schema):
    id: str
    device_type_id: str
    device_type_name: str
    device_type_path: str
    name: str
    display_name: str
    sort: int = 0
    is_active: bool = True
    remark: str = ''
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class DeviceOptionNode(Schema):
    value: str
    label: str
    disabled: bool = False
    node_type: str = 'type'
    children: List['DeviceOptionNode'] = Field(default_factory=list)


class EnvironmentAnnouncementIn(Schema):
    title: str = ''
    content_html: str = ''
    enabled: bool = False


class EnvironmentAnnouncementOut(Schema):
    id: Optional[str] = None
    title: str = ''
    content_html: str = ''
    enabled: bool = False
    updated_at: Optional[datetime] = None


class EnvironmentDeviceBrief(Schema):
    id: str
    name: str
    device_type_id: str
    device_type_name: str
    device_type_path: str
    display_name: str


class EnvironmentIn(Schema):
    ip_address: str
    account: str = ''
    password: Optional[str] = None
    domain: str = 'cockpit'
    category: str = 'test'
    project_name: str = ''
    vehicle_model: str = ''
    device_ids: List[str] = Field(default_factory=list)
    config_description: str = ''
    shelf_location: str = ''
    remark: str = ''
    sort: int = 0


class EnvironmentOut(Schema):
    id: str
    ip_address: str
    account: str = ''
    password: str = ''
    can_view_secret: bool = False
    can_use_environment: bool = False
    domain: str
    domain_label: str
    category: str
    category_label: str
    project_name: str
    vehicle_model: str
    device_ids: List[str] = Field(default_factory=list)
    devices: List[EnvironmentDeviceBrief] = Field(default_factory=list)
    device_display: str
    config_description: str = ''
    shelf_location: str
    remark: str = ''
    status: str
    status_label: str
    current_user_id: Optional[str] = None
    current_user_name: str = ''
    occupied_at: Optional[datetime] = None
    occupied_seconds: int = 0
    is_favorite: bool = False
    queue_count: int = 0
    my_queue_id: Optional[str] = None
    my_queue_position: Optional[int] = None
    first_queue_user_name: str = ''
    rdp_url: str = ''
    sort: int = 0
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class EnvironmentListQuery(Schema):
    domain: Optional[str] = None
    category: Optional[str] = None
    project_name: Optional[str] = None
    vehicle_model: Optional[str] = None
    keyword: Optional[str] = None
    favorite_only: bool = False
    page: int = 1
    pageSize: int = 20


class EnvironmentPageOut(Schema):
    items: List[EnvironmentOut]
    total: int
    page: int
    limit: int


class EnvironmentActionOut(Schema):
    success: bool
    message: str
    environment: EnvironmentOut


class QueueItemOut(Schema):
    id: str
    user_id: str
    user_name: str
    queue_type: str
    queue_type_label: str
    position: int
    requested_at: datetime
    is_me: bool = False


class RecordOut(Schema):
    id: str
    operator_id: Optional[str] = None
    operator_name: str = ''
    action: str
    action_label: str
    message: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    sys_create_datetime: datetime


class RecordPageOut(Schema):
    items: List[RecordOut]
    total: int
    page: int
    limit: int
