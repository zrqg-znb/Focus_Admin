from __future__ import annotations

from django.test import TestCase

from apps.deepaudit.audit_rule.audit_rule_model import AuditRuleSet
from apps.deepaudit.audit_rule import audit_rule_services
from apps.deepaudit.c_family import C_FAMILY_SYSTEM_RULE_SET_NAME


class AuditRuleSeedTestCase(TestCase):
    def test_ensure_default_rule_sets_creates_scenario_presets(self) -> None:
        created = audit_rule_services.ensure_default_rule_sets()

        names = set(
            AuditRuleSet.objects.filter(is_deleted=False, is_system=True)
            .values_list('name', flat=True)
        )

        self.assertGreaterEqual(created, 5)
        self.assertIn('场景 A - 并发资源访问规则集', names)
        self.assertIn('场景 B - 高危 API 调用链规则集', names)
        self.assertIn('场景 C - 临界区与硬件访问规则集', names)

        c_family_rule_set = AuditRuleSet.objects.get(name=C_FAMILY_SYSTEM_RULE_SET_NAME, is_system=True, is_deleted=False)
        rule_categories = set(c_family_rule_set.rules.filter(is_deleted=False).values_list('category', flat=True))
        self.assertIn('embedded_concurrency', rule_categories)
        self.assertIn('hardware_access', rule_categories)
