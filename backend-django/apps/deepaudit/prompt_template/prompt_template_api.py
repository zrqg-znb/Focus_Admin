from __future__ import annotations

from ninja import Router

from . import prompt_template_services
from .prompt_template_schemas import (
    PromptTemplateListSchema,
    PromptTemplateSaveSchema,
    PromptTemplateSchema,
    PromptTemplateTestResultSchema,
    PromptTemplateTestSchema,
    PromptTemplateUpdateSchema,
)

router = Router(tags=['DeepAudit-Prompts'])


@router.get('', response=PromptTemplateListSchema, summary='获取提示词模板列表')
def list_prompt_templates(request, keyword: str = '', template_type: str = '', is_active: bool | None = None, page: int = 1, pageSize: int = 20):
    return prompt_template_services.list_templates(
        request.auth,
        keyword=keyword,
        template_type=template_type,
        is_active=is_active,
        page=page,
        page_size=pageSize,
    )


@router.post('/test', response=PromptTemplateTestResultSchema, summary='测试提示词模板')
def test_prompt_template(request, data: PromptTemplateTestSchema):
    return prompt_template_services.test_template(request.auth, data.dict())


@router.get('/{template_id}', response=PromptTemplateSchema, summary='获取提示词模板详情')
def get_prompt_template(request, template_id: str):
    return prompt_template_services.serialize_template(prompt_template_services.get_template(request.auth, template_id))


@router.post('', response=PromptTemplateSchema, summary='创建提示词模板')
def create_prompt_template(request, data: PromptTemplateSaveSchema):
    instance = prompt_template_services.create_template(request.auth, data.dict())
    return prompt_template_services.serialize_template(instance)


@router.put('/{template_id}', response=PromptTemplateSchema, summary='更新提示词模板')
def update_prompt_template(request, template_id: str, data: PromptTemplateUpdateSchema):
    instance = prompt_template_services.update_template(request.auth, template_id, data.dict(exclude_unset=True))
    return prompt_template_services.serialize_template(instance)


@router.delete('/{template_id}', response=bool, summary='删除提示词模板')
def delete_prompt_template(request, template_id: str):
    return prompt_template_services.delete_template(request.auth, template_id)


@router.post('/{template_id}/set-default', response=bool, summary='设置默认提示词模板')
def set_default_prompt_template(request, template_id: str):
    return prompt_template_services.set_default_template(request.auth, template_id)
