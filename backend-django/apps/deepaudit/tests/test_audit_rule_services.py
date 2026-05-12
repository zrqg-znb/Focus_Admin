from __future__ import annotations

from django.test import TestCase

from apps.deepaudit.audit_rule.audit_rule_model import AuditRuleSet
from apps.deepaudit.audit_rule import audit_rule_services


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
