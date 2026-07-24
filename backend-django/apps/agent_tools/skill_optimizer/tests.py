import io
import zipfile

from django.test import TestCase

from core.user.user_model import User

from .crypto import credential_cipher
from .models import AgentSkillProvider, AgentSkillRun
from .services import _safe_zip_entries, download_run, upload_skill
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
