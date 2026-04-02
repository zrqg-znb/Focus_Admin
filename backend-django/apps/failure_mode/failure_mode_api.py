from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import failure_mode_services
from .failure_mode_schemas import (
    FailureModeCreateSchema,
    FailureModeDictOptionsSchema,
    FailureModeInsightOutSchema,
    FailureModeOutSchema,
    FailureModePageSchema,
    FailureModeSearchSchema,
    FailureModeStatisticsSubsystemPageSchema,
    FailureModeStatisticsSubsystemSearchSchema,
    FailureModeStatisticsSummarySchema,
    FailureModeSubsystemConfigCreateSchema,
    FailureModeSubsystemConfigOptionsSchema,
    FailureModeSubsystemConfigOutSchema,
    FailureModeSubsystemConfigPageSchema,
    FailureModeSubsystemConfigSearchSchema,
    FailureModeSubsystemConfigUpdateSchema,
    FailureModeUpdateSchema,
    HandlingMeasureCreateSchema,
    HandlingMeasureOutSchema,
    HandlingMeasurePageSchema,
    HandlingMeasureSearchSchema,
    HandlingMeasureUpdateSchema,
    HuatuoDiagnosisCreateSchema,
    HuatuoDiagnosisOutSchema,
    HuatuoDiagnosisPageSchema,
    HuatuoDiagnosisUpdateSchema,
    InterceptionInsightOutSchema,
    InterceptionStrategyCreateSchema,
    InterceptionStrategyOutSchema,
    InterceptionStrategyPageSchema,
    InterceptionStrategyUpdateSchema,
    KeywordSearchSchema,
    ObservationMethodCreateSchema,
    ObservationMethodOutSchema,
    ObservationMethodPageSchema,
    ObservationMethodSearchSchema,
    ObservationMethodUpdateSchema,
    SaveSuccessSchema,
    TestCaseCreateSchema,
    TestCaseOutSchema,
    TestCasePageSchema,
    TestCaseUpdateSchema,
)

router = Router(tags=['FailureMode'], auth=GlobalAuth())


@router.get('/dict-options', response=FailureModeDictOptionsSchema, summary='获取故障模式模块字典选项')
def get_dict_options(request):
    return failure_mode_services.get_failure_mode_dict_options()


@router.post('/statistics/summary', response=FailureModeStatisticsSummarySchema, summary='获取故障管理统计摘要')
def get_statistics_summary(request):
    return failure_mode_services.get_failure_mode_statistics_summary()


@router.post('/statistics/subsystems/search', response=FailureModeStatisticsSubsystemPageSchema, summary='搜索故障管理子系统统计表')
def search_statistics_subsystems(request, filters: FailureModeStatisticsSubsystemSearchSchema):
    return failure_mode_services.list_failure_mode_statistics_subsystems(filters)


@router.post('/subsystem-configs/search', response=FailureModeSubsystemConfigPageSchema, summary='搜索故障模式子系统配置列表')
def search_subsystem_configs(request, filters: FailureModeSubsystemConfigSearchSchema):
    return failure_mode_services.list_failure_mode_subsystem_configs(filters)


@router.post('/subsystem-configs', response=FailureModeSubsystemConfigOutSchema, summary='创建故障模式子系统配置')
def create_subsystem_config(request, data: FailureModeSubsystemConfigCreateSchema):
    return failure_mode_services.create_failure_mode_subsystem_config(request, data)


@router.get('/subsystem-configs/options', response=FailureModeSubsystemConfigOptionsSchema, summary='获取故障模式子系统联动选项')
def get_subsystem_config_options(request):
    return failure_mode_services.get_failure_mode_subsystem_config_options()


@router.get('/subsystem-configs/{item_id}', response=FailureModeSubsystemConfigOutSchema, summary='获取故障模式子系统配置详情')
def get_subsystem_config_detail(request, item_id: str):
    return failure_mode_services.get_failure_mode_subsystem_config_detail(item_id)


@router.put('/subsystem-configs/{item_id}', response=FailureModeSubsystemConfigOutSchema, summary='更新故障模式子系统配置')
def update_subsystem_config(request, item_id: str, data: FailureModeSubsystemConfigUpdateSchema):
    return failure_mode_services.update_failure_mode_subsystem_config(request, item_id, data)


@router.delete('/subsystem-configs/{item_id}', response=SaveSuccessSchema, summary='删除故障模式子系统配置')
def delete_subsystem_config(request, item_id: str):
    return failure_mode_services.delete_failure_mode_subsystem_config(item_id)


@router.post('/failure-modes/search', response=FailureModePageSchema, summary='搜索故障模式列表')
def search_failure_modes(request, filters: FailureModeSearchSchema):
    return failure_mode_services.list_failure_modes(filters)


@router.post('/failure-modes', response=FailureModeOutSchema, summary='创建故障模式')
def create_failure_mode(request, data: FailureModeCreateSchema):
    return failure_mode_services.create_failure_mode(request, data)


@router.get('/failure-modes/{failure_mode_id}', response=FailureModeOutSchema, summary='获取故障模式详情')
def get_failure_mode_detail(request, failure_mode_id: str):
    return failure_mode_services.get_failure_mode_detail(failure_mode_id)


@router.get('/failure-modes/{failure_mode_id}/insight', response=FailureModeInsightOutSchema, summary='获取故障模式关联洞察')
def get_failure_mode_insight(request, failure_mode_id: str):
    return failure_mode_services.get_failure_mode_insight(failure_mode_id)


@router.put('/failure-modes/{failure_mode_id}', response=FailureModeOutSchema, summary='更新故障模式')
def update_failure_mode(request, failure_mode_id: str, data: FailureModeUpdateSchema):
    return failure_mode_services.update_failure_mode(request, failure_mode_id, data)


@router.delete('/failure-modes/{failure_mode_id}', response=SaveSuccessSchema, summary='删除故障模式')
def delete_failure_mode(request, failure_mode_id: str):
    return failure_mode_services.delete_failure_mode(failure_mode_id)


@router.post('/interception-strategies/search', response=InterceptionStrategyPageSchema, summary='搜索产线拦截策略列表')
def search_interception_strategies(request, filters: KeywordSearchSchema):
    return failure_mode_services.list_interception_strategies(filters)


@router.post('/interception-strategies', response=InterceptionStrategyOutSchema, summary='创建产线拦截策略')
def create_interception_strategy(request, data: InterceptionStrategyCreateSchema):
    return failure_mode_services.create_interception_strategy(request, data)


@router.get('/interception-strategies/{item_id}', response=InterceptionStrategyOutSchema, summary='获取产线拦截策略详情')
def get_interception_strategy_detail(request, item_id: str):
    return failure_mode_services.get_interception_strategy_detail(item_id)


@router.get('/interception-strategies/{item_id}/insight', response=InterceptionInsightOutSchema, summary='获取产线拦截策略关联洞察')
def get_interception_strategy_insight(request, item_id: str):
    return failure_mode_services.get_interception_strategy_insight(item_id)


@router.put('/interception-strategies/{item_id}', response=InterceptionStrategyOutSchema, summary='更新产线拦截策略')
def update_interception_strategy(request, item_id: str, data: InterceptionStrategyUpdateSchema):
    return failure_mode_services.update_interception_strategy(request, item_id, data)


@router.delete('/interception-strategies/{item_id}', response=SaveSuccessSchema, summary='删除产线拦截策略')
def delete_interception_strategy(request, item_id: str):
    return failure_mode_services.delete_interception_strategy(item_id)


@router.post('/handling-measures/search', response=HandlingMeasurePageSchema, summary='搜索故障处理措施列表')
def search_handling_measures(request, filters: HandlingMeasureSearchSchema):
    return failure_mode_services.list_handling_measures(filters)


@router.post('/handling-measures', response=HandlingMeasureOutSchema, summary='创建故障处理措施')
def create_handling_measure(request, data: HandlingMeasureCreateSchema):
    return failure_mode_services.create_handling_measure(request, data)


@router.get('/handling-measures/{item_id}', response=HandlingMeasureOutSchema, summary='获取故障处理措施详情')
def get_handling_measure_detail(request, item_id: str):
    return failure_mode_services.get_handling_measure_detail(item_id)


@router.put('/handling-measures/{item_id}', response=HandlingMeasureOutSchema, summary='更新故障处理措施')
def update_handling_measure(request, item_id: str, data: HandlingMeasureUpdateSchema):
    return failure_mode_services.update_handling_measure(request, item_id, data)


@router.delete('/handling-measures/{item_id}', response=SaveSuccessSchema, summary='删除故障处理措施')
def delete_handling_measure(request, item_id: str):
    return failure_mode_services.delete_handling_measure(item_id)


@router.post('/observation-methods/search', response=ObservationMethodPageSchema, summary='搜索维测手段列表')
def search_observation_methods(request, filters: ObservationMethodSearchSchema):
    return failure_mode_services.list_observation_methods(filters)


@router.post('/observation-methods', response=ObservationMethodOutSchema, summary='创建维测手段')
def create_observation_method(request, data: ObservationMethodCreateSchema):
    return failure_mode_services.create_observation_method(request, data)


@router.get('/observation-methods/{item_id}', response=ObservationMethodOutSchema, summary='获取维测手段详情')
def get_observation_method_detail(request, item_id: str):
    return failure_mode_services.get_observation_method_detail(item_id)


@router.put('/observation-methods/{item_id}', response=ObservationMethodOutSchema, summary='更新维测手段')
def update_observation_method(request, item_id: str, data: ObservationMethodUpdateSchema):
    return failure_mode_services.update_observation_method(request, item_id, data)


@router.delete('/observation-methods/{item_id}', response=SaveSuccessSchema, summary='删除维测手段')
def delete_observation_method(request, item_id: str):
    return failure_mode_services.delete_observation_method(item_id)


@router.post('/huatuo-diagnoses/search', response=HuatuoDiagnosisPageSchema, summary='搜索华佗诊断方案列表')
def search_huatuo_diagnoses(request, filters: KeywordSearchSchema):
    return failure_mode_services.list_huatuo_diagnoses(filters)


@router.post('/huatuo-diagnoses', response=HuatuoDiagnosisOutSchema, summary='创建华佗诊断方案')
def create_huatuo_diagnosis(request, data: HuatuoDiagnosisCreateSchema):
    return failure_mode_services.create_huatuo_diagnosis(request, data)


@router.get('/huatuo-diagnoses/{item_id}', response=HuatuoDiagnosisOutSchema, summary='获取华佗诊断方案详情')
def get_huatuo_diagnosis_detail(request, item_id: str):
    return failure_mode_services.get_huatuo_diagnosis_detail(item_id)


@router.put('/huatuo-diagnoses/{item_id}', response=HuatuoDiagnosisOutSchema, summary='更新华佗诊断方案')
def update_huatuo_diagnosis(request, item_id: str, data: HuatuoDiagnosisUpdateSchema):
    return failure_mode_services.update_huatuo_diagnosis(request, item_id, data)


@router.delete('/huatuo-diagnoses/{item_id}', response=SaveSuccessSchema, summary='删除华佗诊断方案')
def delete_huatuo_diagnosis(request, item_id: str):
    return failure_mode_services.delete_huatuo_diagnosis(item_id)


@router.post('/test-cases/search', response=TestCasePageSchema, summary='搜索测试用例列表')
def search_test_cases(request, filters: KeywordSearchSchema):
    return failure_mode_services.list_test_cases(filters)


@router.post('/test-cases', response=TestCaseOutSchema, summary='创建测试用例')
def create_test_case(request, data: TestCaseCreateSchema):
    return failure_mode_services.create_test_case(request, data)


@router.get('/test-cases/{item_id}', response=TestCaseOutSchema, summary='获取测试用例详情')
def get_test_case_detail(request, item_id: str):
    return failure_mode_services.get_test_case_detail(item_id)


@router.put('/test-cases/{item_id}', response=TestCaseOutSchema, summary='更新测试用例')
def update_test_case(request, item_id: str, data: TestCaseUpdateSchema):
    return failure_mode_services.update_test_case(request, item_id, data)


@router.delete('/test-cases/{item_id}', response=SaveSuccessSchema, summary='删除测试用例')
def delete_test_case(request, item_id: str):
    return failure_mode_services.delete_test_case(item_id)
