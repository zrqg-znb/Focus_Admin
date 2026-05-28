from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from ninja.errors import HttpError

from core.dict.dict_model import Dict
from core.dict_item.dict_item_model import DictItem
from core.user.user_model import User
from apps.project_manager.project.project_model import Project

from .failure_mode_model import (
    FailureMode,
    FailureModeHandlingMeasureRel,
    FailureModeObservationMethodRel,
    FailureModeProduct,
    HandlingMeasure,
    HuatuoDiagnosis,
    InterceptionStrategy,
    ObservationMethod,
    ProductFailureMode,
    ProductFailureModeHandlingLanding,
    ProductFailureModeHuatuoLanding,
    ProductFailureModeInterceptionLanding,
    ProductFailureModeObservationLanding,
)
from .failure_mode_services import (
    _build_statistics_payload_from_sources,
    _normalize_scope_bindings_for_storage,
    _serialize_failure_mode,
    get_failure_mode_dict_options,
)
from .failure_mode_workflow_services import (
    TaskWorkflowService,
    _build_product_failure_mode_landing_maps,
    _normalize_task_landing_payload_for_item,
    _summarize_task_landing_payload,
    _validate_task_landing_tengwu_requirement_numbers,
)


class ScopeBindingNormalizationTests(SimpleTestCase):
    def test_storage_scope_binding_uses_fallback_subsystem(self):
        bindings = _normalize_scope_bindings_for_storage(
            [
                {
                    'product_id': 'product-1',
                    'product_name': 'Product A',
                }
            ],
            fallback_subsystem='Engine',
        )

        self.assertEqual(
            bindings,
            [{'product_id': 'product-1', 'subsystem': 'Engine'}],
        )

    def test_storage_scope_binding_keeps_explicit_subsystem(self):
        bindings = _normalize_scope_bindings_for_storage(
            [
                {
                    'product_id': 'product-1',
                    'product_name': 'Product A',
                    'subsystem': 'Chassis',
                }
            ],
            fallback_subsystem='Engine',
        )

        self.assertEqual(
            bindings,
            [{'product_id': 'product-1', 'subsystem': 'Chassis'}],
        )

    def test_storage_scope_binding_requires_effective_subsystem(self):
        with self.assertRaises(HttpError) as context:
            _normalize_scope_bindings_for_storage(
                [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                    }
                ],
            )

        self.assertEqual(context.exception.status_code, 422)


class TaskLandingPayloadNormalizationTests(SimpleTestCase):
    def test_fallback_product_status_map_preserves_landed_state(self):
        item = {
            'scope_bindings': [
                {
                    'product_id': 'product-1',
                    'product_name': 'Product A',
                    'subsystem': 'Engine',
                },
            ],
            'interception_strategy_items': [
                {
                    'id': 'resource-1',
                    'label': '产线拦截策略 1',
                    'subtitle': '主拦截',
                },
            ],
        }
        fallback_payload = {
            'products': [
                {
                    'product_id': 'product-1',
                    'product_name': 'Product A',
                    'subsystems': ['Engine'],
                },
            ],
            'interception_status_map_by_product': {
                'product-1': {
                    'resource-1': '已落地',
                },
            },
            'handling_status_map_by_product': {},
            'observation_status_map_by_product': {},
            'huatuo_status_map_by_product': {},
        }

        payload = _normalize_task_landing_payload_for_item(
            item,
            fallback_payload=fallback_payload,
        )

        self.assertEqual(payload['products'][0]['landing_status'], '已落地')
        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0]['landing_status'],
            '已落地',
        )
        self.assertEqual(payload['failure_mode_landing_status'], '已落地')

    def test_landed_product_row_requires_tengwu_requirement_numbers(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'scope_bindings': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystem': 'Engine',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                    },
                ],
            },
            existing_payload={
                'products': [],
                'interception_rows': [
                    {
                        'resource_id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'landing_status': '已落地',
                        'product_rows': [
                            {
                                'product_id': 'product-1',
                                'product_name': 'Product A',
                                'subsystems': ['Engine'],
                                'landing_status': '已落地',
                            },
                        ],
                    },
                ],
                'handling_rows': [],
                'observation_rows': [],
                'huatuo_rows': [],
            },
        )

        with self.assertRaises(HttpError) as context:
            _validate_task_landing_tengwu_requirement_numbers(payload)

        self.assertEqual(context.exception.status_code, 422)
        self.assertFalse(_summarize_task_landing_payload(payload)['landing_completed'])

    def test_landed_product_row_normalizes_tengwu_requirement_numbers(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'scope_bindings': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystem': 'Engine',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                    },
                ],
            },
            existing_payload={
                'products': [],
                'interception_rows': [
                    {
                        'resource_id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'landing_status': '已落地',
                        'product_rows': [
                            {
                                'product_id': 'product-1',
                                'product_name': 'Product A',
                                'subsystems': ['Engine'],
                                'landing_status': '已落地',
                                'tengwu_requirement_numbers': [
                                    ' TW-1 ',
                                    'TW-1',
                                    '',
                                    'TW-2',
                                ],
                            },
                        ],
                    },
                ],
                'handling_rows': [],
                'observation_rows': [],
                'huatuo_rows': [],
            },
        )

        product_row = payload['interception_rows'][0]['product_rows'][0]
        self.assertEqual(
            product_row['tengwu_requirement_numbers'],
            ['TW-1', 'TW-2'],
        )
        _validate_task_landing_tengwu_requirement_numbers(payload)
        self.assertTrue(_summarize_task_landing_payload(payload)['landing_completed'])

    def test_non_landed_product_row_clears_tengwu_requirement_numbers(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'scope_bindings': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystem': 'Engine',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                    },
                ],
            },
            existing_payload={
                'products': [],
                'interception_rows': [
                    {
                        'resource_id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'landing_status': '未落地',
                        'product_rows': [
                            {
                                'product_id': 'product-1',
                                'product_name': 'Product A',
                                'subsystems': ['Engine'],
                                'landing_status': '未落地',
                                'tengwu_requirement_numbers': ['TW-1'],
                            },
                        ],
                    },
                ],
                'handling_rows': [],
                'observation_rows': [],
                'huatuo_rows': [],
            },
        )

        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0][
                'tengwu_requirement_numbers'
            ],
            [],
        )

    def test_fallback_tengwu_requirement_numbers_are_applied(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'scope_bindings': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystem': 'Engine',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                    },
                ],
            },
            fallback_payload={
                'products': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystems': ['Engine'],
                    },
                ],
                'interception_status_map_by_product': {
                    'product-1': {'resource-1': '已落地'},
                },
                'interception_tengwu_numbers_map_by_product': {
                    'product-1': {'resource-1': ['TW-1']},
                },
                'handling_status_map_by_product': {},
                'observation_status_map_by_product': {},
                'huatuo_status_map_by_product': {},
            },
        )

        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0][
                'tengwu_requirement_numbers'
            ],
            ['TW-1'],
        )

    def test_product_only_scope_bindings_fallback_to_failure_mode_subsystem(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'brief': '新故障模式',
                'subsystem': 'Engine',
                'scope_bindings': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'subtitle': '主拦截',
                    },
                ],
            }
        )

        self.assertEqual(payload['products'][0]['subsystems'], ['Engine'])
        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0]['subsystems'],
            ['Engine'],
        )

    def test_existing_payload_keeps_product_names_and_landing_status(self):
        item = {
            'brief': '编辑后的故障模式标题',
            'scope_bindings': [
                {
                    'product_id': 'product-1',
                    'product_name': 'Product A',
                    'subsystem': 'Engine',
                },
            ],
            'interception_strategy_items': [
                {
                    'id': 'resource-1',
                    'label': '产线拦截策略 1',
                    'subtitle': '主拦截',
                },
            ],
        }
        existing_payload = {
            'products': [
                {
                    'product_id': 'product-1',
                    'product_name': 'Product A',
                    'subsystems': ['Engine'],
                    'landing_status': '已落地',
                },
            ],
            'interception_rows': [
                {
                    'resource_id': 'resource-1',
                    'label': '产线拦截策略 1',
                    'subtitle': '主拦截',
                    'group_key': 'interception',
                    'landing_status': '已落地',
                    'product_rows': [
                        {
                            'product_id': 'product-1',
                            'product_name': 'Product A',
                            'subsystems': ['Engine'],
                            'landing_status': '已落地',
                        },
                    ],
                },
            ],
            'handling_rows': [],
            'observation_rows': [],
            'huatuo_rows': [],
        }

        payload = _normalize_task_landing_payload_for_item(
            item,
            existing_payload=existing_payload,
        )

        self.assertEqual(payload['products'][0]['product_name'], 'Product A')
        self.assertEqual(payload['products'][0]['landing_status'], '已落地')
        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0]['product_name'],
            'Product A',
        )
        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0]['landing_status'],
            '已落地',
        )
        self.assertEqual(payload['failure_mode_landing_status'], '已落地')

    def test_existing_payload_merges_new_scope_binding_products(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'brief': '编辑后的故障模式标题',
                'subsystem': 'Engine',
                'scope_bindings': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                    },
                    {
                        'product_id': 'product-2',
                        'product_name': 'Product B',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'subtitle': '主拦截',
                    },
                ],
            },
            existing_payload={
                'products': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystems': ['Engine'],
                        'landing_status': '已落地',
                    },
                ],
                'interception_rows': [
                    {
                        'resource_id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'subtitle': '主拦截',
                        'group_key': 'interception',
                        'landing_status': '已落地',
                        'product_rows': [
                            {
                                'product_id': 'product-1',
                                'product_name': 'Product A',
                                'subsystems': ['Engine'],
                                'landing_status': '已落地',
                            },
                        ],
                    },
                ],
                'handling_rows': [],
                'observation_rows': [],
                'huatuo_rows': [],
            },
        )

        self.assertEqual(
            [item['product_id'] for item in payload['products']],
            ['product-1', 'product-2'],
        )
        self.assertEqual(payload['products'][0]['landing_status'], '已落地')
        self.assertEqual(payload['products'][1]['landing_status'], '未落地')
        self.assertEqual(
            [
                item['product_id']
                for item in payload['interception_rows'][0]['product_rows']
            ],
            ['product-1', 'product-2'],
        )

    def test_existing_payload_removes_deleted_scope_binding_products(self):
        payload = _normalize_task_landing_payload_for_item(
            {
                'brief': '编辑后的故障模式标题',
                'subsystem': 'Engine',
                'scope_bindings': [
                    {
                        'product_id': 'product-2',
                        'product_name': 'Product B',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'subtitle': '主拦截',
                    },
                ],
            },
            existing_payload={
                'products': [
                    {
                        'product_id': 'product-1',
                        'product_name': 'Product A',
                        'subsystems': ['Engine'],
                        'landing_status': '已落地',
                    },
                ],
                'interception_rows': [
                    {
                        'resource_id': 'resource-1',
                        'label': '产线拦截策略 1',
                        'subtitle': '主拦截',
                        'group_key': 'interception',
                        'landing_status': '已落地',
                        'product_rows': [
                            {
                                'product_id': 'product-1',
                                'product_name': 'Product A',
                                'subsystems': ['Engine'],
                                'landing_status': '已落地',
                            },
                        ],
                    },
                ],
                'handling_rows': [],
                'observation_rows': [],
                'huatuo_rows': [],
            },
        )

        self.assertEqual(
            [item['product_id'] for item in payload['products']],
            ['product-2'],
        )
        self.assertEqual(
            [
                item['product_id']
                for item in payload['interception_rows'][0]['product_rows']
            ],
            ['product-2'],
        )


class TaskLandingTengwuPersistenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='fm-tengwu-tester', password='x')
        self.project = Project.objects.create(
            name='Product A',
            domain='Domain',
            type='Vehicle',
            code='FM-TW-A',
        )
        self.product = FailureModeProduct.objects.create(project=self.project)
        self.failure_mode = FailureMode.objects.create(
            brief='FM-TW-001',
            subsystem='Engine',
        )
        self.product_failure_mode = ProductFailureMode.objects.create(
            product=self.product,
            subsystem='Engine',
            failure_mode=self.failure_mode,
        )
        self.interception = InterceptionStrategy.objects.create(
            interception_item='产线拦截策略 1',
            version_detection_html='',
        )
        self.handling = HandlingMeasure.objects.create(
            measure='处理措施 1',
            measure_category='检测',
        )
        self.observation = ObservationMethod.objects.create(
            monitor_type='流水日志',
            log_id='LOG-1',
        )
        self.huatuo = HuatuoDiagnosis.objects.create(description='诊断方案 1')

    def test_product_landing_table_fallback_carries_tengwu_requirement_numbers(self):
        ProductFailureModeInterceptionLanding.objects.create(
            product_failure_mode=self.product_failure_mode,
            interception_strategy=self.interception,
            landing_status='已落地',
            is_landed=True,
            tengwu_requirement_numbers=['TW-1'],
        )

        fallback_payload = _build_product_failure_mode_landing_maps(
            self.product_failure_mode,
        )
        payload = _normalize_task_landing_payload_for_item(
            {
                'scope_bindings': [
                    {
                        'product_id': str(self.product.id),
                        'product_name': self.project.name,
                        'subsystem': 'Engine',
                    },
                ],
                'interception_strategy_items': [
                    {
                        'id': str(self.interception.id),
                        'label': self.interception.interception_item,
                    },
                ],
            },
            fallback_payload=fallback_payload,
        )

        self.assertEqual(
            payload['interception_rows'][0]['product_rows'][0][
                'tengwu_requirement_numbers'
            ],
            ['TW-1'],
        )

    def test_sync_product_failure_mode_landings_writes_tengwu_requirement_numbers(self):
        product_row = {
            'product_id': str(self.product.id),
            'product_name': self.project.name,
            'subsystems': ['Engine'],
            'landing_status': '已落地',
            'tengwu_requirement_numbers': [' TW-1 ', 'TW-1', 'TW-2'],
        }
        payload = {
            'products': [product_row],
            'interception_rows': [
                {
                    'resource_id': str(self.interception.id),
                    'landing_status': '已落地',
                    'product_rows': [product_row],
                },
            ],
            'handling_rows': [
                {
                    'resource_id': str(self.handling.id),
                    'landing_status': '已落地',
                    'product_rows': [
                        {
                            **product_row,
                            'tengwu_requirement_numbers': ['TW-H'],
                        },
                    ],
                },
            ],
            'observation_rows': [
                {
                    'resource_id': str(self.observation.id),
                    'landing_status': '已落地',
                    'product_rows': [
                        {
                            **product_row,
                            'tengwu_requirement_numbers': ['TW-O'],
                        },
                    ],
                },
            ],
            'huatuo_rows': [
                {
                    'resource_id': str(self.huatuo.id),
                    'landing_status': '未落地',
                    'product_rows': [
                        {
                            **product_row,
                            'landing_status': '未落地',
                            'tengwu_requirement_numbers': ['TW-SHOULD-CLEAR'],
                        },
                    ],
                },
            ],
        }

        TaskWorkflowService._sync_product_failure_mode_landings(
            self.product_failure_mode,
            payload,
            self.user,
        )

        self.assertEqual(
            ProductFailureModeInterceptionLanding.objects.get().tengwu_requirement_numbers,
            ['TW-1', 'TW-2'],
        )
        self.assertEqual(
            ProductFailureModeHandlingLanding.objects.get().tengwu_requirement_numbers,
            ['TW-H'],
        )
        self.assertEqual(
            ProductFailureModeObservationLanding.objects.get().tengwu_requirement_numbers,
            ['TW-O'],
        )
        self.assertEqual(
            ProductFailureModeHuatuoLanding.objects.get().tengwu_requirement_numbers,
            [],
        )


class FailureModeDictDrivenCategoryTests(TestCase):
    def setUp(self):
        self._create_dict_items(
            'failure_mode_measure_category',
            ['前置校验', '自动恢复'],
        )
        self._create_dict_items(
            'failure_mode_monitor_type',
            ['系统日志', '遥测点位'],
        )

    def _create_dict_items(self, code: str, labels: list[str]):
        dict_obj = Dict.objects.create(name=code, code=code)
        total = len(labels)
        for index, label in enumerate(labels):
            DictItem.objects.create(
                dict=dict_obj,
                label=label,
                value=label,
                sort=total - index,
            )

    def _extract_dataset_value(self, rows: list[dict[str, int | str]], name: str) -> int:
        for item in rows:
            if item['name'] == name:
                return int(item['value'])
        return 0

    def test_serialize_and_dict_options_follow_dict_order_with_history_extras(self):
        failure_mode = FailureMode.objects.create(
            brief='FM-001',
            subsystem='Drive',
            effect_html='<p>影响</p>',
            root_cause_html='<p>根因</p>',
            required_handling_measure_categories=['自动恢复', '历史类别'],
            required_observation_method_types=['系统日志', '历史类型'],
        )
        handling_measure = HandlingMeasure.objects.create(
            measure='历史处理措施',
            measure_category='历史类别',
        )
        observation_method = ObservationMethod.objects.create(
            monitor_type='历史类型',
            log_id='log-001',
        )
        FailureModeHandlingMeasureRel.objects.create(
            failure_mode=failure_mode,
            handling_measure=handling_measure,
        )
        FailureModeObservationMethodRel.objects.create(
            failure_mode=failure_mode,
            observation_method=observation_method,
        )

        detail = _serialize_failure_mode(failure_mode)
        self.assertEqual(
            detail['required_handling_measure_categories'],
            ['自动恢复', '历史类别'],
        )
        self.assertEqual(
            detail['required_observation_method_types'],
            ['系统日志', '历史类型'],
        )

        dict_options = get_failure_mode_dict_options()
        self.assertEqual(
            [item['value'] for item in dict_options['measure_category']],
            ['前置校验', '自动恢复'],
        )
        self.assertEqual(
            [item['value'] for item in dict_options['monitor_type']],
            ['系统日志', '遥测点位'],
        )

        payload = _build_statistics_payload_from_sources(
            [SimpleNamespace(subsystem='Drive', failure_mode=failure_mode)],
        )
        summary = payload['summary']
        row = payload['rows'][0]

        self.assertEqual(
            list(summary['handling_status_map'].keys()),
            ['前置校验', '自动恢复', '历史类别'],
        )
        self.assertEqual(
            list(summary['observation_status_map'].keys()),
            ['系统日志', '遥测点位', '历史类型'],
        )
        self.assertEqual(
            row['handling_relation_counts'],
            {'前置校验': 0, '自动恢复': 0, '历史类别': 1},
        )
        self.assertEqual(
            row['observation_relation_counts'],
            {'系统日志': 0, '遥测点位': 0, '历史类型': 1},
        )
        self.assertEqual(
            self._extract_dataset_value(
                summary['handling_status_map']['前置校验'],
                '无需配置',
            ),
            1,
        )
        self.assertEqual(
            self._extract_dataset_value(
                summary['handling_status_map']['自动恢复'],
                '待补充',
            ),
            1,
        )
        self.assertEqual(
            self._extract_dataset_value(
                summary['handling_status_map']['历史类别'],
                '已配置',
            ),
            1,
        )
