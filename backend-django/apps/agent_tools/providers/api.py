from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import services
from .schemas import ProviderIn, ProviderOut, ProviderTestOut

router = Router(tags=['AgentTools-Providers'], auth=GlobalAuth())


@router.get('', response=list[ProviderOut], summary='模型档案列表')
def list_provider_configs(request):
    """返回当前用户在 AI 辅助工具中可使用的模型档案。"""
    return services.list_providers(request.auth)


@router.post('', response=ProviderOut, summary='创建模型档案')
def create_provider_config(request, payload: ProviderIn):
    """创建 OpenAI 兼容模型档案，凭证仅会被加密保存。"""
    return services.save_provider(request.auth, payload)


@router.put('/{provider_id}', response=ProviderOut, summary='更新模型档案')
def update_provider_config(request, provider_id: str, payload: ProviderIn):
    """更新模型档案；空 API Key 不会覆盖既有凭证。"""
    return services.save_provider(request.auth, payload, provider_id)


@router.post('/{provider_id}/test', response=ProviderTestOut, summary='测试模型档案')
def test_provider_config(request, provider_id: str):
    """验证模型连接、API Key 和模型名称是否可用。"""
    return services.test_provider(request.auth, provider_id)
