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

    def test_build_markdown_renders_domain_sections_and_html_tables(self):
        """Markdown 导出应按领域分段，并用 HTML 表格合并二级和三级节点。"""
        user = self._user('u1', '张三<PL>')
        reviewer = self._user('u2', '李四')
        root = self._node(
            '座舱领域',
            code='D-001',
            description='<p>根节点说明</p>',
            linked_project=SimpleNamespace(name='项目一'),
            children=[
                self._node(
                    '二级系统',
                    code='S-001',
                    description='<p>二级说明</p>',
                    positions=[self._position('系统PL', [reviewer])],
                    children=[
                        self._node(
                            '三级组件',
                            description='<p>组件<br>说明 & 备注</p>',
                            positions=[
                                self._position('开发Owner', [user]),
                                self._position('测试Owner', []),
                            ],
                            children=[
                                self._node(
                                    '四级模块',
                                    description='<b>模块说明</b>',
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        with patch.object(services, 'get_tree_data', return_value=[root]):
            markdown = services.build_delivery_matrix_markdown()

        self.assertIn('# 沟通矩阵', markdown)
        self.assertIn('## 座舱领域', markdown)
        self.assertIn('<table>', markdown)
        self.assertIn(
            '<tr><th>二级节点</th><th>三级节点</th><th>岗位</th><th>人员</th><th>描述</th></tr>',
            markdown,
        )
        self.assertIn('<td rowspan="4">二级系统</td>', markdown)
        self.assertIn('<td rowspan="2">三级组件</td>', markdown)
        self.assertIn('<td>三级组件 / 四级模块</td>', markdown)
        self.assertIn('<strong>开发Owner</strong>', markdown)
        self.assertIn('<strong>张三&lt;PL&gt;</strong>', markdown)
        self.assertIn('<strong>测试Owner</strong>', markdown)
        self.assertIn('<strong>李四</strong>', markdown)
        self.assertIn('组件 说明 &amp; 备注', markdown)
        self.assertIn('<td>模块说明</td>', markdown)
        self.assertNotIn('导出时间', markdown)
        self.assertNotIn('节点数量', markdown)
        self.assertNotIn('岗位数量', markdown)
        self.assertNotIn('人员数量', markdown)
        self.assertNotIn('层级路径', markdown)
        self.assertNotIn('节点编码', markdown)
        self.assertNotIn('关联项目', markdown)
        self.assertNotIn('D-001', markdown)
        self.assertNotIn('S-001', markdown)
        self.assertNotIn('项目一', markdown)

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
