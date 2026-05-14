from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.deepaudit.c_family import C_FAMILY_TARGET_VULNERABILITIES
from apps.deepaudit.scenario_profile import (
    AUTO_SCENARIO_KEY,
    API_CHAIN_SCENARIO_KEY,
    CONCURRENCY_SCENARIO_KEY,
    GENERAL_SCENARIO_KEY,
    LEGACY_C_FAMILY_SCENARIO_KEY,
    resolve_scenario_profile,
)


class ScenarioProfileResolverTestCase(SimpleTestCase):
    databases = {"default"}

    def setUp(self) -> None:
        self.c_family_project = SimpleNamespace(programming_languages='["c", "cpp"]')

    def test_explicit_scenario_a_resolves_to_concurrency_profile(self) -> None:
        profile = resolve_scenario_profile(
            "A",
            project=self.c_family_project,
            file_paths=["src/main.c"],
        )

        self.assertEqual(profile["scenario_key"], CONCURRENCY_SCENARIO_KEY)
        self.assertEqual(profile["resolved_scenario_key"], CONCURRENCY_SCENARIO_KEY)
        self.assertIn("race_condition", profile["target_vulnerabilities"])
        self.assertIn("deadlock", profile["target_vulnerabilities"])
        self.assertIn("embedded_concurrency", profile["target_vulnerabilities"])
        self.assertIn("race_condition", profile["knowledge_modules"])

    def test_auto_falls_back_to_legacy_c_family_for_c_projects(self) -> None:
        profile = resolve_scenario_profile(
            None,
            project=self.c_family_project,
            file_paths=["src/main.c"],
        )

        self.assertEqual(profile["scenario_key"], AUTO_SCENARIO_KEY)
        self.assertEqual(profile["resolved_scenario_key"], LEGACY_C_FAMILY_SCENARIO_KEY)
        self.assertTrue(profile["legacy_c_family"])
        self.assertEqual(profile["target_vulnerabilities"], C_FAMILY_TARGET_VULNERABILITIES)

    def test_auto_detects_c_family_from_concrete_file_paths_without_project_languages(self) -> None:
        profile = resolve_scenario_profile(
            None,
            project=None,
            file_paths=["drivers/can/main.c", "include/can_driver.h"],
        )

        self.assertEqual(profile["scenario_key"], AUTO_SCENARIO_KEY)
        self.assertEqual(profile["resolved_scenario_key"], LEGACY_C_FAMILY_SCENARIO_KEY)
        self.assertTrue(profile["legacy_c_family"])
        self.assertEqual(profile["target_vulnerabilities"], C_FAMILY_TARGET_VULNERABILITIES)

    def test_general_scenario_suppresses_c_family_fallback(self) -> None:
        profile = resolve_scenario_profile(
            "general",
            project=self.c_family_project,
            file_paths=["src/main.c"],
        )

        self.assertEqual(profile["scenario_key"], GENERAL_SCENARIO_KEY)
        self.assertFalse(profile["legacy_c_family"])
        self.assertEqual(profile["knowledge_modules"], [])
        self.assertEqual(profile["resolution_reason"], "explicit_general")

    def test_unknown_scenario_falls_back_to_general(self) -> None:
        profile = resolve_scenario_profile("unknown-scenario", project=self.c_family_project)

        self.assertEqual(profile["scenario_key"], GENERAL_SCENARIO_KEY)
        self.assertEqual(profile["resolution_reason"], "unknown_scenario_fallback")
        self.assertFalse(profile["legacy_c_family"])

    def test_explicit_b_scenario_maps_to_api_chain_profile(self) -> None:
        profile = resolve_scenario_profile(
            "B",
            project=SimpleNamespace(programming_languages='["python"]'),
        )

        self.assertEqual(profile["scenario_key"], API_CHAIN_SCENARIO_KEY)
        self.assertIn("buffer_overflow", profile["target_vulnerabilities"])
        self.assertIn("use_after_free", profile["target_vulnerabilities"])
        self.assertIn("resource_leak", profile["knowledge_modules"])
