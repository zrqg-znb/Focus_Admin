from datetime import datetime

from ninja import Schema


class ProviderIn(Schema):
    """模型连接的可编辑字段；接口永不回传 API Key。"""

    name: str
    base_url: str
    model: str
    api_key: str = ''
    is_active: bool = True
    description: str = ''


class ProviderOut(Schema):
    """模型连接的安全展示字段。"""

    id: str
    name: str
    base_url: str
    model: str
    has_api_key: bool
    is_active: bool
    description: str
    owner_name: str = ''
    sys_create_datetime: datetime | None = None


class ProviderTestOut(Schema):
    """模型连通性探测结果。"""

    ok: bool
    message: str
