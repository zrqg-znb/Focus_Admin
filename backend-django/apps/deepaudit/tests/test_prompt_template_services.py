from __future__ import annotations

from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.test import Client, SimpleTestCase, TestCase
from django.urls import resolve

from apps.deepaudit.llm.service import _load_prompt_template_content
from apps.deepaudit.prompt_template import prompt_template_services
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate
from core.user.user_model import User


class PromptTemplateRoutingTestCase(SimpleTestCase):
    def test_prompts_test_route_resolves_to_static_endpoint(self) -> None:
        match = resolve('/api/deepaudit/prompts/test')

        self.assertEqual(match.url_name, 'test_prompt_template')

    def test_prompts_test_route_no_longer_returns_405(self) -> None:
        response = Client().post(
            '/api/deepaudit/prompts/test',
            data='{}',
            content_type='application/json',
        )

        self.assertNotEqual(response.status_code, 405)


class PromptTemplateContentLoadingTestCase(TestCase):
    def test_load_prompt_template_content_allows_explicit_non_system_type(self) -> None:
        template = PromptTemplate.objects.create(
            name='analysis-template',
            template_type='analysis',
            content_zh='中文模板',
            content_en='English template',
            is_active=True,
            is_system=True,
        )

        template_name, content = async_to_sync(_load_prompt_template_content)(
            str(template.id),
            output_language='zh-CN',
            use_default_template=False,
        )

        self.assertEqual(template_name, 'analysis-template')
        self.assertEqual(content, '中文模板')

    def test_load_prompt_template_content_uses_default_active_template_even_if_not_system_type(self) -> None:
        PromptTemplate.objects.create(
            name='default-analysis-template',
            template_type='analysis',
            content_zh='默认中文模板',
            content_en='Default English template',
            is_default=True,
            is_active=True,
            is_system=True,
        )

        template_name, content = async_to_sync(_load_prompt_template_content)(
            None,
            output_language='zh-CN',
            use_default_template=True,
        )

        self.assertEqual(template_name, 'default-analysis-template')
        self.assertEqual(content, '默认中文模板')


class PromptTemplateTestingServiceTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='prompt-owner',
            password='not-used',
            name='Prompt Owner',
        )

    @patch('apps.deepaudit.prompt_template.prompt_template_services.user_config_services.get_user_config')
    @patch('apps.deepaudit.prompt_template.prompt_template_services.LLMService')
    def test_test_template_uses_llm_service_with_custom_prompt(
        self,
        mock_llm_service,
        mock_get_user_config,
    ) -> None:
        mock_get_user_config.return_value = {'llm_config': {}, 'other_config': {}}
        service = mock_llm_service.return_value
        service.analyze_code_with_custom_prompt = AsyncMock(
            return_value={
                'issues': [],
                'quality_score': 92,
                'summary': {'total_issues': 0},
            }
        )

        result = prompt_template_services.test_template(
            self.user,
            {
                'content': '请审计这段 C 代码',
                'language': 'c',
                'code': 'int main(void) { return 0; }',
                'output_language': 'zh',
            },
        )

        self.assertTrue(result['success'])
        mock_get_user_config.assert_called_once_with(self.user)
        service.analyze_code_with_custom_prompt.assert_awaited_once_with(
            'int main(void) { return 0; }',
            'c',
            '请审计这段 C 代码',
            output_language='zh',
        )

    @patch('apps.deepaudit.prompt_template.prompt_template_services.user_config_services.get_user_config')
    @patch('apps.deepaudit.prompt_template.prompt_template_services.LLMService')
    def test_test_template_returns_explicit_error_when_llm_fails(
        self,
        mock_llm_service,
        mock_get_user_config,
    ) -> None:
        mock_get_user_config.return_value = {'llm_config': {}, 'other_config': {}}
        service = mock_llm_service.return_value
        service.analyze_code_with_custom_prompt = AsyncMock(
            side_effect=RuntimeError('LLM unavailable')
        )

        result = prompt_template_services.test_template(
            self.user,
            {
                'content': '请审计这段 C 代码',
                'language': 'c',
                'code': 'int main(void) { return 0; }',
                'output_language': 'zh',
            },
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['result'], {})
        self.assertIn('LLM unavailable', result['error'])


class PromptTemplateSeedTestCase(TestCase):
    def test_ensure_default_templates_creates_scenario_presets(self) -> None:
        created = prompt_template_services.ensure_default_templates()

        names = set(
            PromptTemplate.objects.filter(is_deleted=False, is_system=True)
            .values_list('name', flat=True)
        )

        self.assertGreaterEqual(created, 6)
        self.assertIn('场景 A - 并发资源代码梳理', names)
        self.assertIn('场景 B - 高危 API 调用链梳理', names)
        self.assertIn('场景 C - 临界区与硬件访问检查', names)
