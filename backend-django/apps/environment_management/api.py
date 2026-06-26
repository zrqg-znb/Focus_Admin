from ninja import Query, Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import services
from .schemas import (
    DeviceOptionNode,
    DeviceTypeIn,
    DeviceTypeOut,
    EnvironmentAnnouncementIn,
    EnvironmentAnnouncementOut,
    EnvironmentActionOut,
    EnvironmentIn,
    EnvironmentListQuery,
    EnvironmentOut,
    EnvironmentPageOut,
    QueueItemOut,
    RecordPageOut,
    TestDeviceIn,
    TestDeviceOut,
)

router = Router(tags=['EnvironmentManagement'], auth=GlobalAuth())


@router.get('/device-types', response=list[DeviceTypeOut], summary='测试设备类型树')
def list_device_types(request, active_only: bool = False):
    """返回测试设备类型树；管理端用它组织左侧类型树和具体测试设备归类。"""
    services.require_manager(request.auth)
    return services.list_device_type_tree(active_only=active_only)


@router.post('/device-types', response=list[DeviceTypeOut], summary='新建测试设备类型')
def create_device_type(request, payload: DeviceTypeIn):
    """新增测试设备类型，并返回最新类型树供前端直接刷新。"""
    return services.create_device_type(request.auth, payload)


@router.put('/device-types/{type_id}', response=list[DeviceTypeOut], summary='更新测试设备类型')
def update_device_type(request, type_id: str, payload: DeviceTypeIn):
    """更新测试设备类型；服务层会校验父子层级合法性。"""
    return services.update_device_type(request.auth, type_id, payload)


@router.delete('/device-types/{type_id}', response=bool, summary='删除测试设备类型')
def delete_device_type(request, type_id: str):
    """删除测试设备类型；已被环境设备实例使用的类型会被拒绝删除。"""
    return services.delete_device_type(request.auth, type_id)


@router.get('/devices', response=list[TestDeviceOut], summary='测试设备列表')
def list_devices(
    request,
    device_type_id: str = '',
    keyword: str = '',
    active_only: bool = False,
    device_type_ids: str = '',
    name: str = '',
    type_keyword: str = '',
    is_active_values: str = '',
    remark: str = '',
):
    """返回测试设备主数据列表；环境配置会先选择这里维护的具体测试设备。"""
    services.require_manager(request.auth)
    return services.list_devices(
        device_type_id or None,
        keyword or None,
        active_only=active_only,
        device_type_ids=device_type_ids or None,
        name=name or None,
        type_keyword=type_keyword or None,
        is_active_values=is_active_values or None,
        remark=remark or None,
    )


@router.post('/devices', response=TestDeviceOut, summary='新建测试设备')
def create_device(request, payload: TestDeviceIn):
    """新增测试设备主数据，供环境配置实例引用。"""
    return services.create_device(request.auth, payload)


@router.put('/devices/{device_id}', response=TestDeviceOut, summary='更新测试设备')
def update_device(request, device_id: str, payload: TestDeviceIn):
    """更新测试设备主数据；已绑定环境的实例会继续引用该设备。"""
    return services.update_device(request.auth, device_id, payload)


@router.delete('/devices/{device_id}', response=bool, summary='删除测试设备')
def delete_device(request, device_id: str):
    """删除测试设备主数据；已被环境实例绑定时会拒绝删除。"""
    return services.delete_device(request.auth, device_id)


@router.get('/device-options', response=list[DeviceOptionNode], summary='测试设备级联选择项')
def list_device_options(request):
    """返回测试设备级联选项；类型节点作为路径容器，叶子设备用于环境实例选择。"""
    services.require_manager(request.auth)
    return services.list_device_options()


@router.get('/filter-options', response=dict, summary='环境管理筛选选项')
def list_filter_options(request):
    """返回表头筛选下拉选项；选项不包含密码、RDP 地址等敏感字段。"""
    return services.list_filter_options(request.auth)


@router.get('/announcement', response=EnvironmentAnnouncementOut, summary='环境操作公告')
def get_announcement(request):
    """读取占用/排队前展示的环境公告；未配置时返回禁用空公告。"""
    return services.get_announcement()


@router.put('/announcement', response=EnvironmentAnnouncementOut, summary='保存环境操作公告')
def save_announcement(request, payload: EnvironmentAnnouncementIn):
    """保存环境操作公告，仅环境管理员可维护。"""
    return services.save_announcement(request.auth, payload)


@router.get('/environments', response=EnvironmentPageOut, summary='环境列表')
def list_environments(request, query: EnvironmentListQuery = Query(...)):
    """分页返回环境列表；账号可见但密码不下发，设备按环境实例结构返回。"""
    return services.list_environments(request.auth, query)


@router.post('/environments', response=EnvironmentOut, summary='新建环境')
def create_environment(request, payload: EnvironmentIn):
    """新建环境配置，支持提交环境设备实例和历史 device_ids 兼容字段。"""
    return services.create_environment(request.auth, payload)


@router.put('/environments/{environment_id}', response=EnvironmentOut, summary='更新环境')
def update_environment(request, environment_id: str, payload: EnvironmentIn):
    """更新环境配置；密码为空时由服务层按兼容规则处理，不会在响应中返回。"""
    return services.update_environment(request.auth, environment_id, payload)


@router.delete('/environments/{environment_id}', response=bool, summary='删除环境')
def delete_environment(request, environment_id: str):
    """软删除环境；被占用的环境由服务层拒绝删除。"""
    return services.delete_environment(request.auth, environment_id)


@router.post('/environments/{environment_id}/favorite', response=EnvironmentOut, summary='收藏环境')
def favorite_environment(request, environment_id: str):
    """收藏环境，用于用户端全部/收藏视图和收藏优先排序。"""
    return services.set_favorite(request.auth, environment_id, True)


@router.delete('/environments/{environment_id}/favorite', response=EnvironmentOut, summary='取消收藏环境')
def unfavorite_environment(request, environment_id: str):
    """取消收藏环境，并返回更新后的环境 DTO。"""
    return services.set_favorite(request.auth, environment_id, False)


@router.post('/environments/{environment_id}/occupy', response=EnvironmentActionOut, summary='占用环境')
def occupy_environment(request, environment_id: str):
    """申请占用环境；成功后前端才允许触发 Focus RDP 启动器。"""
    return services.occupy_environment(request.auth, environment_id)


@router.post('/environments/{environment_id}/release', response=EnvironmentActionOut, summary='释放环境')
def release_environment(request, environment_id: str):
    """释放当前占用；释放后仅通知队首可手动占用，不自动转交。"""
    return services.release_environment(request.auth, environment_id)


@router.post('/environments/{environment_id}/queue', response=EnvironmentOut, summary='排队')
def queue_environment(request, environment_id: str):
    """加入普通等待队列；前端仅在环境被占用时展示排队入口。"""
    return services.enqueue_environment(request.auth, environment_id, 'normal')


@router.post('/environments/{environment_id}/jump-queue', response=EnvironmentOut, summary='插队')
def jump_queue_environment(request, environment_id: str):
    """插队接口保留给后续版本；当前前端已隐藏入口。"""
    return services.enqueue_environment(request.auth, environment_id, 'jump')


@router.delete('/environments/{environment_id}/queue/me', response=EnvironmentOut, summary='取消我的排队')
def cancel_my_queue(request, environment_id: str):
    """取消当前用户在该环境的等待记录，并触发队列重排。"""
    return services.cancel_my_queue(request.auth, environment_id)


@router.get('/environments/{environment_id}/queue', response=list[QueueItemOut], summary='排队情况')
def list_queue(request, environment_id: str):
    """查看当前等待队列，平台默认用户也可查看排队情况。"""
    return services.list_queue(request.auth, environment_id)


@router.get('/environments/{environment_id}/records', response=RecordPageOut, summary='占用记录')
def list_records(request, environment_id: str, page: int = 1, pageSize: int = 20):
    """分页查看环境占用与队列操作记录，避免历史记录过多拖慢弹窗。"""
    return services.list_records(environment_id, page=page, page_size=pageSize)
