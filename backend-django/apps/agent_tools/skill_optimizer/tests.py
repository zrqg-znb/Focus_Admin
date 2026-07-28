import io
import json
import zipfile
from unittest.mock import MagicMock, patch

from django.test import TestCase
from ninja.errors import HttpError
from requests import Response

from core.user.user_model import User

from ..providers.crypto import credential_cipher
from ..providers.models import AgentSkillProvider
from ..providers.services import normalize_upstream_text
from .models import AgentSkillRun, AgentSkillTrace
from .services import _chat_completion, _safe_zip_entries, configure_run, download_run, list_traces, start_run, upload_skill
from .schemas import SkillOut


def make_skill_zip(skill_md: str, extra: dict[str, bytes] | None = None) -> bytes:
    """构造测试用 ZIP，避免依赖外部技能项目文件。"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('demo/SKILL.md', skill_md)
        for path, content in (extra or {}).items():
            archive.writestr(f'demo/{path}', content)
    return output.getvalue()


class SkillOptimizerServiceTests(TestCase):
    """验证 Agent Tools / Skill Optimizer 的安全存储边界。"""

    def setUp(self):
        self.user = User.objects.create(username='tools-test', password='pass', name='Tools Test')

    def test_api_key_is_encrypted_and_decryptable(self):
        """模块自有加密器不能将 API Key 明文写入持久化字段。"""
        encrypted = credential_cipher.encrypt('sk-test-secret')
        self.assertNotEqual(encrypted, 'sk-test-secret')
        self.assertEqual(credential_cipher.decrypt(encrypted), 'sk-test-secret')

    def test_skill_upload_validates_and_preserves_non_text_files(self):
        """上传只解析文本 SKILL.md，但 ZIP 内资源仍会留在原始归档中。"""
        content = make_skill_zip('---\nname: demo\ndescription: Demo skill\n---\n# Demo', {'assets/icon.bin': b'\x00\x01'})
        skill = upload_skill(self.user, 'demo.zip', content)
        self.assertEqual(skill['name'], 'demo')
        self.assertIn('demo/assets/icon.bin', skill['file_manifest'])

    def test_upload_api_accepts_datetime_response(self):
        """上传接口响应中的时间字段应允许 Django 返回 datetime 对象。"""
        payload = {
            'id': 'skill-id', 'name': 'demo', 'description': '', 'original_filename': 'demo.zip',
            'file_manifest': ['SKILL.md'], 'sys_creator_name': 'Tools Test',
            'sys_create_datetime': self.user.sys_create_datetime,
        }
        self.assertEqual(SkillOut.model_validate(payload).sys_create_datetime, self.user.sys_create_datetime)

    def test_unsafe_zip_path_is_rejected(self):
        """路径穿越条目必须在进入数据库前被拒绝。"""
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('../SKILL.md', '# unsafe')
        from ninja.errors import HttpError
        with self.assertRaises(HttpError):
            _safe_zip_entries(output.getvalue())

    def test_download_replaces_skill_md_and_preserves_assets(self):
        """完成任务的下载包只替换 SKILL.md，不改写其他资源。"""
        original = '---\nname: demo\n---\n# Original'
        skill_data = upload_skill(self.user, 'demo.zip', make_skill_zip(original, {'assets/logo.bin': b'asset'}))
        provider = AgentSkillProvider.objects.create(name='test-provider', base_url='https://example.com/v1', model='test', api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user)
        from .models import AgentSkill
        skill = AgentSkill.objects.get(id=skill_data['id'])
        run = AgentSkillRun.objects.create(skill=skill, provider=provider, provider_snapshot={'name': provider.name, 'model': provider.model}, status='completed', original_skill_md=original, improved_skill_md='---\nname: demo\n---\n# Improved', sys_creator=self.user, sys_modifier=self.user)
        response = download_run(str(run.id))
        archive = zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content)))
        self.assertEqual(archive.read('demo/SKILL.md').decode(), '---\nname: demo\n---\n# Improved')
        self.assertEqual(archive.read('demo/assets/logo.bin'), b'asset')

    def test_start_run_records_the_actual_queue_entry_time(self):
        """进度告警必须以投递时间为准，而不是用户最初创建草稿的时间。"""
        skill_data = upload_skill(self.user, 'queued.zip', make_skill_zip('# Queue'))
        provider = AgentSkillProvider.objects.create(
            name='queued-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        from .models import AgentSkill
        run = AgentSkillRun.objects.create(
            skill=AgentSkill.objects.get(id=skill_data['id']), provider=provider, provider_snapshot={},
            scenarios=[{'id': 1, 'name': 'case', 'input': 'hello'}],
            evaluations=[{'id': 1, 'name': 'rule', 'question': 'ok?', 'pass_condition': 'yes'}],
            status='draft', original_skill_md='# Queue', sys_creator=self.user, sys_modifier=self.user,
        )
        with patch('apps.agent_tools.tasks.dispatch_agent_skill_run', return_value=None) as dispatch:
            response = start_run(self.user, str(run.id))
        run.refresh_from_db()
        self.assertEqual(response['status'], 'queued')
        self.assertEqual(run.status, 'queued')
        self.assertIsNotNone(run.queued_at)
        dispatch.assert_called_once()

    def test_chat_completion_reports_non_json_provider_response(self):
        """网关 HTML 页面不能再被转换为不可读的 JSONDecodeError。"""
        provider = AgentSkillProvider.objects.create(
            name='html-response-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        response = Response()
        response.status_code = 200
        response.headers['Content-Type'] = 'text/html'
        response._content = b'<html>Not Found</html>'
        with patch('apps.agent_tools.providers.services.requests.post', return_value=response) as post:
            with self.assertRaisesRegex(RuntimeError, '非 JSON 响应'):
                _chat_completion(provider, [{'role': 'user', 'content': 'hello'}])
        self.assertEqual(post.call_args.args[0], 'https://example.com/v1/chat/completions')

    def test_chat_completion_accepts_complete_endpoint_url(self):
        """用户填写完整 Chat Completions 地址时不应重复拼接路径。"""
        provider = AgentSkillProvider.objects.create(
            name='complete-endpoint-provider', base_url='https://example.com/v1/chat/completions', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        response = Response()
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        response._content = b'{"choices":[{"message":{"content":"OK"}}]}'
        with patch('apps.agent_tools.providers.services.requests.post', return_value=response) as post:
            self.assertEqual(_chat_completion(provider, [{'role': 'user', 'content': 'hello'}]), 'OK')
        self.assertEqual(post.call_args.args[0], 'https://example.com/v1/chat/completions')

    def test_regenerate_config_returns_upstream_error(self):
        """重新生成配置应把模型错误转换为可显示的 502 业务错误。"""
        skill_data = upload_skill(self.user, 'demo.zip', make_skill_zip('# Demo'))
        provider = AgentSkillProvider.objects.create(
            name='config-error-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        from .models import AgentSkill
        skill = AgentSkill.objects.get(id=skill_data['id'])
        run = AgentSkillRun.objects.create(
            skill=skill, provider=provider, provider_snapshot={}, status='draft', original_skill_md='# Demo',
            sys_creator=self.user, sys_modifier=self.user,
        )
        payload = type('Payload', (), {'scenarios': [], 'evaluations': []})()
        with patch('apps.agent_tools.skill_optimizer.services._generate_config', side_effect=RuntimeError('上游返回 HTML')):
            with self.assertRaisesRegex(HttpError, '生成评测配置失败') as context:
                configure_run(self.user, str(run.id), payload, regenerate=True)
        self.assertEqual(context.exception.status_code, 502)

    def test_chat_completion_persists_auditable_trace(self):
        """运行中的模型调用应保存请求、响应、阶段与耗时，供前端活动流展示。"""
        skill_data = upload_skill(self.user, 'trace.zip', make_skill_zip('# Trace'))
        provider = AgentSkillProvider.objects.create(
            name='trace-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        from .models import AgentSkill
        run = AgentSkillRun.objects.create(
            skill=AgentSkill.objects.get(id=skill_data['id']), provider=provider, provider_snapshot={},
            status='running', original_skill_md='# Trace', sys_creator=self.user, sys_modifier=self.user,
        )
        response = Response()
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        response._content = b'{"choices":[{"message":{"content":"model reply"}}]}'
        with patch('apps.agent_tools.providers.services.requests.post', return_value=response):
            _chat_completion(
                provider, [{'role': 'user', 'content': 'trace request'}], run=run,
                stage='baseline_response', round_number=0,
            )
        trace = AgentSkillTrace.objects.get(run=run)
        self.assertEqual(trace.status, 'completed')
        self.assertEqual(trace.stage, 'baseline_response')
        self.assertIn('trace request', trace.request_content)
        self.assertEqual(trace.response_content, 'model reply')
        self.assertGreaterEqual(trace.duration_ms, 0)

    def test_chat_completion_streams_partial_response_into_trace(self):
        """OpenAI 兼容 SSE 分块输出应在调用结束前持续写入可见轨迹。"""
        skill_data = upload_skill(self.user, 'stream.zip', make_skill_zip('# Stream'))
        provider = AgentSkillProvider.objects.create(
            name='stream-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        from .models import AgentSkill
        run = AgentSkillRun.objects.create(
            skill=AgentSkill.objects.get(id=skill_data['id']), provider=provider, provider_snapshot={},
            status='running', original_skill_md='# Stream', sys_creator=self.user, sys_modifier=self.user,
        )
        response = MagicMock()
        response.ok = True
        response.headers = {'Content-Type': 'text/event-stream'}
        response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"first "}}]}',
            'data: {"choices":[{"delta":{"content":"chunk"}}]}',
            'data: [DONE]',
        ]
        with patch('apps.agent_tools.providers.services.requests.post', return_value=response):
            self.assertEqual(
                _chat_completion(
                    provider, [{'role': 'user', 'content': 'stream request'}], run=run,
                    stage='baseline_response', round_number=0,
                ),
                'first chunk',
            )
        trace = AgentSkillTrace.objects.get(run=run)
        self.assertEqual(trace.status, 'completed')
        self.assertEqual(trace.response_content, 'first chunk')

    def test_stream_decodes_utf8_bytes_and_repairs_known_mojibake(self):
        """流式轨迹必须保留中文与弯引号，不能受上游错误 charset 影响。"""
        skill_data = upload_skill(self.user, 'encoding.zip', make_skill_zip('# Encoding'))
        provider = AgentSkillProvider.objects.create(
            name='encoding-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        from .models import AgentSkill
        run = AgentSkillRun.objects.create(
            skill=AgentSkill.objects.get(id=skill_data['id']), provider=provider, provider_snapshot={},
            status='running', original_skill_md='# Encoding', sys_creator=self.user, sys_modifier=self.user,
        )
        expected = 'I’m making one change：需求设计'
        response = MagicMock()
        response.ok = True
        response.headers = {'Content-Type': 'text/event-stream'}
        payload = json.dumps({'choices': [{'delta': {'content': expected}}]}, ensure_ascii=False)
        response.iter_lines.return_value = [f'data: {payload}'.encode('utf-8'), b'data: [DONE]']
        with patch('apps.agent_tools.providers.services.requests.post', return_value=response):
            self.assertEqual(
                _chat_completion(
                    provider, [{'role': 'user', 'content': 'encoding request'}], run=run,
                    stage='baseline_response', round_number=0,
                ),
                expected,
            )
        doubly_mojibaked = expected.encode('utf-8').decode('latin-1').encode('utf-8').decode('latin-1')
        self.assertEqual(normalize_upstream_text(doubly_mojibaked), expected)

    def test_list_traces_repairs_existing_mojibake_without_data_migration(self):
        """历史轨迹在读取时修复，避免要求用户重新运行已完成的任务。"""
        skill_data = upload_skill(self.user, 'history.zip', make_skill_zip('# History'))
        provider = AgentSkillProvider.objects.create(
            name='history-provider', base_url='https://example.com/v1', model='test',
            api_key_encrypted=credential_cipher.encrypt('key'), sys_creator=self.user, sys_modifier=self.user,
        )
        from .models import AgentSkill
        run = AgentSkillRun.objects.create(
            skill=AgentSkill.objects.get(id=skill_data['id']), provider=provider, provider_snapshot={},
            status='completed', original_skill_md='# History', sys_creator=self.user, sys_modifier=self.user,
        )
        expected = 'I’m making one change：需求设计'
        AgentSkillTrace.objects.create(
            run=run,
            response_content=expected.encode('utf-8').decode('latin-1').encode('utf-8').decode('latin-1'),
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        self.assertEqual(list_traces(str(run.id))[0]['response_content'], expected)
