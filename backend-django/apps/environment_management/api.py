from ninja import Query, Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import services
from .schemas import (
    EnvironmentActionOut,
    EnvironmentIn,
    EnvironmentListQuery,
    EnvironmentOut,
    EnvironmentPageOut,
    QueueItemOut,
    RecordPageOut,
)

router = Router(tags=['EnvironmentManagement'], auth=GlobalAuth())


@router.get('/environments', response=EnvironmentPageOut, summary='环境列表')
def list_environments(request, query: EnvironmentListQuery = Query(...)):
    return services.list_environments(request.auth, query)


@router.post('/environments', response=EnvironmentOut, summary='新建环境')
def create_environment(request, payload: EnvironmentIn):
    return services.create_environment(request.auth, payload)


@router.put('/environments/{environment_id}', response=EnvironmentOut, summary='更新环境')
def update_environment(request, environment_id: str, payload: EnvironmentIn):
    return services.update_environment(request.auth, environment_id, payload)


@router.delete('/environments/{environment_id}', response=bool, summary='删除环境')
def delete_environment(request, environment_id: str):
    return services.delete_environment(request.auth, environment_id)


@router.post('/environments/{environment_id}/favorite', response=EnvironmentOut, summary='收藏环境')
def favorite_environment(request, environment_id: str):
    return services.set_favorite(request.auth, environment_id, True)


@router.delete('/environments/{environment_id}/favorite', response=EnvironmentOut, summary='取消收藏环境')
def unfavorite_environment(request, environment_id: str):
    return services.set_favorite(request.auth, environment_id, False)


@router.post('/environments/{environment_id}/occupy', response=EnvironmentActionOut, summary='占用环境')
def occupy_environment(request, environment_id: str):
    return services.occupy_environment(request.auth, environment_id)


@router.post('/environments/{environment_id}/release', response=EnvironmentActionOut, summary='释放环境')
def release_environment(request, environment_id: str):
    return services.release_environment(request.auth, environment_id)


@router.post('/environments/{environment_id}/queue', response=EnvironmentOut, summary='排队')
def queue_environment(request, environment_id: str):
    return services.enqueue_environment(request.auth, environment_id, 'normal')


@router.post('/environments/{environment_id}/jump-queue', response=EnvironmentOut, summary='插队')
def jump_queue_environment(request, environment_id: str):
    return services.enqueue_environment(request.auth, environment_id, 'jump')


@router.delete('/environments/{environment_id}/queue/me', response=EnvironmentOut, summary='取消我的排队')
def cancel_my_queue(request, environment_id: str):
    return services.cancel_my_queue(request.auth, environment_id)


@router.get('/environments/{environment_id}/queue', response=list[QueueItemOut], summary='排队情况')
def list_queue(request, environment_id: str):
    return services.list_queue(request.auth, environment_id)


@router.get('/environments/{environment_id}/records', response=RecordPageOut, summary='占用记录')
def list_records(request, environment_id: str, page: int = 1, pageSize: int = 20):
    return services.list_records(environment_id, page=page, page_size=pageSize)
