from __future__ import annotations

from django.test import SimpleTestCase

from .failure_mode_workflow_services import _normalize_task_landing_payload_for_item


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
