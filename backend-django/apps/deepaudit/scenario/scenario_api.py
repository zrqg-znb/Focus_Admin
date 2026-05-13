from __future__ import annotations

from ninja import Router

from . import scenario_services
from .scenario_schemas import (
    ScenarioProfileCopySchema,
    ScenarioProfileListSchema,
    ScenarioProfileSaveSchema,
    ScenarioProfileSchema,
    ScenarioProfileUpdateSchema,
)

router = Router(tags=['DeepAudit-Scenarios'])


@router.get('', response=ScenarioProfileListSchema, summary='获取场景列表')
def list_scenarios(request, keyword: str = '', objective_type: str = '', is_active: bool | None = None, page: int = 1, pageSize: int = 20):
    return scenario_services.list_scenarios(
        request.auth,
        keyword=keyword,
        objective_type=objective_type,
        is_active=is_active,
        page=page,
        page_size=pageSize,
    )


@router.get('/{scenario_id}', response=ScenarioProfileSchema, summary='获取场景详情')
def get_scenario(request, scenario_id: str):
    return scenario_services.serialize_scenario(scenario_services.get_scenario(request.auth, scenario_id))


@router.post('', response=ScenarioProfileSchema, summary='创建场景')
def create_scenario(request, data: ScenarioProfileSaveSchema):
    return scenario_services.serialize_scenario(scenario_services.create_scenario(request.auth, data.dict()))


@router.put('/{scenario_id}', response=ScenarioProfileSchema, summary='更新场景')
def update_scenario(request, scenario_id: str, data: ScenarioProfileUpdateSchema):
    return scenario_services.serialize_scenario(scenario_services.update_scenario(request.auth, scenario_id, data.dict(exclude_unset=True)))


@router.post('/{scenario_id}/copy', response=ScenarioProfileSchema, summary='复制场景')
def copy_scenario(request, scenario_id: str, data: ScenarioProfileCopySchema):
    return scenario_services.serialize_scenario(scenario_services.copy_scenario(request.auth, scenario_id, data.dict(exclude_unset=True)))


@router.delete('/{scenario_id}', response=bool, summary='删除场景')
def delete_scenario(request, scenario_id: str):
    return scenario_services.delete_scenario(request.auth, scenario_id)


@router.post('/{scenario_id}/set-default', response=bool, summary='设为默认场景')
def set_default_scenario(request, scenario_id: str):
    return scenario_services.set_default_scenario(request.auth, scenario_id)
