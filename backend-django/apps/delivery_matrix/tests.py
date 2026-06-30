from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.delivery_matrix import services


class _Users:
    def __init__(self, users):
        self._users = users

    def all(self):
        return self._users


class DeliveryMatrixMarkdownTests(TestCase):
    def _user(self, user_id, name, username=''):
        return SimpleNamespace(id=user_id, name=name, username=username)

    def _position(self, name, users):
        return SimpleNamespace(name=name, users=_Users(users))

    def _node(self, name, **kwargs):
        return SimpleNamespace(
            name=name,
            code=kwargs.get('code'),
            description=kwargs.get('description'),
            linked_project=kwargs.get('linked_project'),
            position_list=kwargs.get('positions', []),
            child_list=kwargs.get('children', []),
        )

    def test_build_markdown_escapes_table_cells_and_flattens_tree(self):
        """Markdown 导出应稳定展示层级、岗位人员和转义后的表格内容。"""
        user = self._user('u1', '张三|PL')
        root = self._node(
            '领域|A',
            code='D|A',
            description='<p>根节点<br>说明 | 特殊</p>',
            linked_project=SimpleNamespace(name='项目|一'),
            positions=[self._position('PL', [user])],
            children=[
                self._node(
                    '组件B',
                    description='<script>alert(1)</script><b>组件说明</b>',
                )
            ],
        )

        with patch.object(services, 'get_tree_data', return_value=[root]):
            markdown = services.build_delivery_matrix_markdown()

        self.assertIn('# 沟通矩阵', markdown)
        self.assertIn('- 节点数量：2', markdown)
        self.assertIn('- 岗位数量：1', markdown)
        self.assertIn('- 人员数量：1', markdown)
        self.assertIn('领域\\|A / 组件B', markdown)
        self.assertIn('张三\\|PL', markdown)
        self.assertIn('项目\\|一', markdown)
        self.assertIn('根节点说明 \\| 特殊', markdown)
        self.assertNotIn('<script>', markdown)

    def test_export_markdown_response_headers(self):
        """Markdown 导出接口响应应携带下载文件名和正确内容类型。"""
        with patch.object(services, 'build_delivery_matrix_markdown', return_value='# 沟通矩阵\n'):
            response = services.export_delivery_matrix_markdown()

        self.assertEqual(response['Content-Type'], 'text/markdown; charset=utf-8')
        self.assertIn('attachment; filename="delivery-matrix-', response['Content-Disposition'])
        self.assertIn('.md"', response['Content-Disposition'])
        self.assertIn('# 沟通矩阵', response.content.decode('utf-8'))

    def test_notify_placeholder_runs_after_commit(self):
        """配置变更通知占位应等事务提交成功后再执行。"""
        actor = SimpleNamespace(id='u1')
        request = SimpleNamespace(auth=actor)

        with patch.object(services, 'notify_delivery_matrix_config_changed') as mocked:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                services._notify_config_changed_on_commit(
                    request,
                    'update_node',
                    {'node_id': 'n1'},
                )

        self.assertEqual(len(callbacks), 1)
        mocked.assert_called_once_with(
            actor=actor,
            action='update_node',
            payload={'node_id': 'n1'},
        )
