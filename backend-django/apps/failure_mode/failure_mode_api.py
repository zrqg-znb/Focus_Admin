from ninja import Query, Router
from ninja.pagination import paginate

from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination

from . import failure_mode_services
from .failure_mode_schemas import (
    FailureModeCreateSchema,
    FailureModeDictOptionsSchema,
    FailureModeFilterSchema,
    FailureModeOutSchema,
    FailureModeUpdateSchema,
    HandlingMeasureCreateSchema,
    HandlingMeasureFilterSchema,
    HandlingMeasureOutSchema,
    HandlingMeasureUpdateSchema,
    HuatuoDiagnosisCreateSchema,
    HuatuoDiagnosisOutSchema,
    HuatuoDiagnosisUpdateSchema,
    InterceptionStrategyCreateSchema,
    InterceptionStrategyOutSchema,
    InterceptionStrategyUpdateSchema,
    KeywordFilterSchema,
    ObservationMethodCreateSchema,
    ObservationMethodFilterSchema,
    ObservationMethodOutSchema,
    ObservationMethodUpdateSchema,
    SaveSuccessSchema,
    TestCaseCreateSchema,
    TestCaseOutSchema,
    TestCaseUpdateSchema,
)

router = Router(tags=['FailureMode'], auth=GlobalAuth())


@router.get('/dict-options', response=FailureModeDictOptionsSchema, summary='获取故障模式模块字典选项')
def get_dict_options(request):
    return failure_mode_services.get_failure_mode_dict_options()


@router.get('/failure-modes', response=list[FailureModeOutSchema], summary='获取故障模式列表')
@paginate(MyPagination, pass_parameter='page_params')
def list_failure_modes(request, filters: FailureModeFilterSchema = Query(...), page_params=None):
    return failure_mode_services.list_failure_modes(filters, page_params)


@router.post('/failure-modes', response=FailureModeOutSchema, summary='创建故障模式')
def create_failure_mode(request, data: FailureModeCreateSchema):
    return failure_mode_services.create_failure_mode(request, data)


@router.get('/failure-modes/{failure_mode_id}', response=FailureModeOutSchema, summary='获取故障模式详情')
def get_failure_mode_detail(request, failure_mode_id: str):
    return failure_mode_services.get_failure_mode_detail(failure_mode_id)


@router.put('/failure-modes/{failure_mode_id}', response=FailureModeOutSchema, summary='更新故障模式')
def update_failure_mode(request, failure_mode_id: str, data: FailureModeUpdateSchema):
    return failure_mode_services.update_failure_mode(request, failure_mode_id, data)


@router.delete('/failure-modes/{failure_mode_id}', response=SaveSuccessSchema, summary='删除故障模式')
def delete_failure_mode(request, failure_mode_id: str):
    return failure_mode_services.delete_failure_mode(failure_mode_id)


@router.get('/interception-strategies', response=list[InterceptionStrategyOutSchema], summary='获取产线拦截策略列表')
@paginate(MyPagination, pass_parameter='page_params')
def list_interception_strategies(request, filters: KeywordFilterSchema = Query(...), page_params=None):
    return failure_mode_services.list_interception_strategies(filters, page_params)


@router.post('/interception-strategies', response=InterceptionStrategyOutSchema, summary='创建产线拦截策略')
def create_interception_strategy(request, data: InterceptionStrategyCreateSchema):
    return failure_mode_services.create_interception_strategy(request, data)


@router.get('/interception-strategies/{item_id}', response=InterceptionStrategyOutSchema, summary='获取产线拦截策略详情')
def get_interception_strategy_detail(request, item_id: str):
    return failure_mode_services.get_interception_strategy_detail(item_id)


@router.put('/interception-strategies/{item_id}', response=InterceptionStrategyOutSchema, summary='更新产线拦截策略')
def update_interception_strategy(request, item_id: str, data: InterceptionStrategyUpdateSchema):
    return failure_mode_services.update_interception_strategy(request, item_id, data)


@router.delete('/interception-strategies/{item_id}', response=SaveSuccessSchema, summary='删除产线拦截策略')
def delete_interception_strategy(request, item_id: str):
    return failure_mode_services.delete_interception_strategy(item_id)


@router.get('/handling-measures', response=list[HandlingMeasureOutSchema], summary='获取故障处理措施列表')
@paginate(MyPagination, pass_parameter='page_params')
def list_handling_measures(request, filters: HandlingMeasureFilterSchema = Query(...), page_params=None):
    return failure_mode_services.list_handling_measures(filters, page_params)


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


@router.get('/observation-methods', response=list[ObservationMethodOutSchema], summary='获取维测手段列表')
@paginate(MyPagination, pass_parameter='page_params')
def list_observation_methods(request, filters: ObservationMethodFilterSchema = Query(...), page_params=None):
    return failure_mode_services.list_observation_methods(filters, page_params)


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


@router.get('/huatuo-diagnoses', response=list[HuatuoDiagnosisOutSchema], summary='获取华佗诊断方案列表')
@paginate(MyPagination, pass_parameter='page_params')
def list_huatuo_diagnoses(request, filters: KeywordFilterSchema = Query(...), page_params=None):
    return failure_mode_services.list_huatuo_diagnoses(filters, page_params)


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


@router.get('/test-cases', response=list[TestCaseOutSchema], summary='获取测试用例列表')
@paginate(MyPagination, pass_parameter='page_params')
def list_test_cases(request, filters: KeywordFilterSchema = Query(...), page_params=None):
    return failure_mode_services.list_test_cases(filters, page_params)


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
