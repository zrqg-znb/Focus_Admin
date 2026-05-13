from __future__ import annotations

from django.test import TestCase

from apps.deepaudit.scenario.scenario_model import AuditScenarioProfile, ScenarioObjectiveType
from apps.deepaudit.scenario.scenario_services import (
    copy_scenario,
    create_scenario,
    ensure_default_scenarios,
    serialize_scenario,
    set_default_scenario,
)
from apps.deepaudit.scenario_profile import (
    API_CHAIN_SCENARIO_KEY,
    CONCURRENCY_SCENARIO_KEY,
    GENERAL_SCENARIO_KEY,
    resolve_scenario_profile,
)
from core.user.user_model import User


class ScenarioServicesTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='scenario-owner',
            password='not-used',
            name='Scenario Owner',
        )

    def test_create_scenario_avoids_general_runtime_leakage_for_custom_inventory_profile(self) -> None:
        scenario = create_scenario(
            self.user,
            {
                'scenario_key': 'repo_inventory',
                'name': '仓库资源梳理',
                'objective_type': ScenarioObjectiveType.INVENTORY,
                'knowledge_modules': [],
            },
        )

        runtime_profile = resolve_scenario_profile(scenario.scenario_key)
        serialized = serialize_scenario(scenario)

        self.assertEqual(runtime_profile['scenario_key'], 'repo_inventory')
        self.assertEqual(runtime_profile['objective_type'], ScenarioObjectiveType.INVENTORY)
        self.assertEqual(runtime_profile['resolution_reason'], 'db_profile')
        self.assertEqual(runtime_profile['target_vulnerabilities'], [])
        self.assertEqual(runtime_profile['focus_keywords'], [])
        self.assertEqual(runtime_profile['tool_policy']['search_code']['keywords'], [])
        self.assertIsNone(serialized['prompt_template_name'])
        self.assertIsNone(serialized['rule_set_name'])

    def test_copy_scenario_preserves_inventory_objective(self) -> None:
        scenario = create_scenario(
            self.user,
            {
                'scenario_key': 'concurrency_inventory',
                'name': '并发代码梳理',
                'objective_type': ScenarioObjectiveType.INVENTORY,
            },
        )

        clone = copy_scenario(self.user, str(scenario.id), {})

        self.assertNotEqual(clone.scenario_key, scenario.scenario_key)
        self.assertEqual(clone.objective_type, ScenarioObjectiveType.INVENTORY)
        self.assertFalse(clone.is_system)

    def test_set_default_scenario_switches_user_default(self) -> None:
        first = create_scenario(
            self.user,
            {
                'scenario_key': 'scenario_alpha',
                'name': 'Alpha',
                'objective_type': ScenarioObjectiveType.AUDIT,
                'is_default': True,
            },
        )
        second = create_scenario(
            self.user,
            {
                'scenario_key': 'scenario_beta',
                'name': 'Beta',
                'objective_type': ScenarioObjectiveType.INVENTORY,
            },
        )

        set_default_scenario(self.user, str(second.id))
        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_ensure_default_scenarios_creates_three_public_presets(self) -> None:
        created = ensure_default_scenarios()

        keys = set(
            AuditScenarioProfile.objects.filter(is_deleted=False, is_system=True)
            .values_list('scenario_key', flat=True)
        )

        self.assertGreaterEqual(created, 3)
        self.assertIn(GENERAL_SCENARIO_KEY, keys)
        self.assertIn(CONCURRENCY_SCENARIO_KEY, keys)
        self.assertIn(API_CHAIN_SCENARIO_KEY, keys)
