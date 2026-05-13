from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.deepaudit.scan_profile import build_prompt_context


class ScanProfileKeywordMappingTestCase(SimpleTestCase):
    def test_prompt_context_picks_up_embedded_concurrency_and_hardware_terms(self) -> None:
        template = SimpleNamespace(
            name='汽车底层 C 审计',
            description='检查 ISR、DMA、MMIO、mutex 和 critical section 的协作。',
            content_zh=(
                '重点关注 taskENTER_CRITICAL、taskEXIT_CRITICAL、readl、writel、volatile、'
                'IRQ、DMA 和 register access。'
            ),
            content_en='',
        )

        context = build_prompt_context(template, 'standard')

        self.assertIn('embedded_concurrency', context['focus'])
        self.assertIn('hardware_access', context['focus'])
        self.assertEqual(context['hint'], '标准模式：平衡覆盖率和审计成本。')
