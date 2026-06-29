from __future__ import annotations

from django.test import SimpleTestCase

from apps.deepaudit.agent_engine.knowledge import (
    MODULE_ALIASES,
    knowledge_loader,
    normalize_module_name,
    resolve_module_alias,
    security_knowledge_rag,
)


class AutomotiveCKnowledgeBaselineTestCase(SimpleTestCase):
    def test_builtin_automotive_c_documents_are_registered(self) -> None:
        document_ids = {item['id'] for item in security_knowledge_rag.list_documents()}

        for expected_id in {
            'autosar_cpp14_rules',
            'autosar_classic_platform',
            'autosar_bsw_contracts',
            'autosar_os_isr_task_contracts',
            'c_memory_ownership',
            'c_interrupt_boundary',
            'c_driver_init_sequence',
            'c_ring_buffer',
            'c_mmio_register_access',
            'c_dma_buffer_lifecycle',
            'c_api_contract_boundary',
            'c_safe_copy_and_bounds',
            'c_resource_cleanup_unwind',
            'misra_c_baseline',
            'cert_c_baseline',
            'autosar_c_baseline',
        }:
            self.assertIn(expected_id, document_ids)

        self.assertEqual(security_knowledge_rag.get_document('misra')['id'], 'misra_c_baseline')
        self.assertEqual(security_knowledge_rag.get_document('autosar')['id'], 'autosar_c_baseline')
        self.assertEqual(security_knowledge_rag.get_document('autosar_cpp14')['id'], 'autosar_cpp14_rules')
        self.assertEqual(security_knowledge_rag.get_document('bsw')['id'], 'autosar_bsw_contracts')
        self.assertEqual(security_knowledge_rag.get_document('mmio')['id'], 'c_mmio_register_access')
        self.assertEqual(security_knowledge_rag.get_document('driver_init_sequence')['id'], 'c_driver_init_sequence')
        self.assertEqual(security_knowledge_rag.get_document('django')['id'], 'framework_django')

    def test_common_aliases_resolve_to_canonical_module_ids(self) -> None:
        self.assertEqual(resolve_module_alias('misra'), 'misra_c_baseline')
        self.assertEqual(resolve_module_alias('autosar_cpp14'), 'autosar_cpp14_rules')
        self.assertEqual(resolve_module_alias('mcal'), 'autosar_bsw_contracts')
        self.assertEqual(resolve_module_alias('autosar_os'), 'autosar_os_isr_task_contracts')
        self.assertEqual(resolve_module_alias('hardcoded_secret'), 'vuln_hardcoded_secrets')
        self.assertEqual(resolve_module_alias('memory_ownership'), 'c_memory_ownership')
        self.assertEqual(resolve_module_alias('driver_init'), 'c_driver_init_sequence')
        self.assertEqual(resolve_module_alias('mmio_register_access'), 'c_mmio_register_access')
        self.assertEqual(normalize_module_name('framework_django'), 'django')
        self.assertEqual(normalize_module_name('vuln_buffer_overflow'), 'buffer_overflow')
        self.assertIn('misra', MODULE_ALIASES)
        self.assertIn('driver_init_sequence', MODULE_ALIASES)

    def test_knowledge_loader_accepts_aliases_and_deduplicates_prompt_sections(self) -> None:
        validation = knowledge_loader.validate_modules(
            ['misra', 'autosar', 'autosar_cpp14', 'bsw', 'autosar_os', 'rtos', 'mmio', 'ring_buffer', 'cleanup', 'contract', 'driver_init']
        )
        self.assertEqual(validation['invalid'], [])
        self.assertTrue({
            'misra_c_baseline',
            'autosar_c_baseline',
            'autosar_cpp14_rules',
            'autosar_bsw_contracts',
            'autosar_os_isr_task_contracts',
            'c_interrupt_boundary',
        }.issubset(set(validation['valid'])))

        prompt = knowledge_loader.build_system_prompt_with_modules(
            'Base prompt',
            ['misra', 'misra_c_baseline', 'mmio', 'driver_init', 'autosar_cpp14', 'bsw'],
        )
        self.assertIn('MISRA C 基线检查', prompt)
        self.assertIn('MMIO / 寄存器访问模式', prompt)
        self.assertIn('驱动初始化顺序与失败回滚', prompt)
        self.assertIn('AUTOSAR C++14 证据化审计规则', prompt)
        self.assertIn('AUTOSAR BSW/RTE/MCAL 接口契约', prompt)
        self.assertEqual(prompt.count('MISRA C 基线检查'), 1)
