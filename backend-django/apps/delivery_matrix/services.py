import html
import re

from django.db import transaction
from django.http import HttpResponse
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.html import strip_tags
from common import fu_crud
from .models import OrganizationNode, PositionStaff
from .schemas import OrgNodeCreate, OrgNodeUpdate, PositionStaffCreate


def notify_delivery_matrix_config_changed(
    actor,
    action: str,
    target_user=None,
    payload: dict | None = None,
):
    """沟通矩阵配置变更通知占位。

    生产环境接入消息中心时，在这里根据 actor、action、target_user 和 payload
    组装通知内容并发送给目标用户。当前版本只保留统一入口，避免业务代码散落通知细节。
    """
    # TODO: 接入生产消息通知服务。
    return None


def _notify_config_changed_on_commit(request, action: str, payload: dict | None = None):
    """在事务成功提交后触发沟通矩阵配置变更通知占位。"""
    actor = getattr(request, 'auth', None)
    transaction.on_commit(
        lambda: notify_delivery_matrix_config_changed(
            actor=actor,
            action=action,
            payload=payload or {},
        )
    )


def _normalize_position_payload(pos_data):
    """统一岗位入参结构，兼容 Ninja Schema 和普通 dict。"""
    if isinstance(pos_data, dict):
        return pos_data.copy()
    return pos_data.dict()


def _replace_node_positions(
    node: OrganizationNode,
    positions: list[PositionStaffCreate],
):
    """整体替换节点岗位人员配置，用于节点编辑和独立岗位更新接口。"""
    node.positions.all().delete()

    result = []
    for pos_data in positions:
        p_dict = _normalize_position_payload(pos_data)
        user_ids = p_dict.pop('user_ids', [])
        position = PositionStaff.objects.create(node=node, **p_dict)
        if user_ids:
            position.users.set(user_ids)
        result.append(position)

    return result


def _plain_text(value):
    """将富文本描述转换为适合 Markdown 表格展示的纯文本。"""
    source = re.sub(r'<\s*br\s*/?>', ' ', str(value or ''), flags=re.IGNORECASE)
    text = html.unescape(strip_tags(source))
    return re.sub(r'\s+', ' ', text).strip()


def _label_text(value):
    """格式化节点、岗位和人员名称，这类字段不是富文本，不剥离尖括号内容。"""
    text = html.unescape(str(value or ''))
    return re.sub(r'\s+', ' ', text).strip()


def _html_cell(value):
    """转义 HTML 表格单元格内容，避免导出数据破坏表格结构。"""
    text = _plain_text(value)
    if not text:
        return '-'
    return html.escape(text, quote=True)


def _html_label(value):
    """转义名称类表格内容，保留原始名称中的特殊字符。"""
    text = _label_text(value)
    if not text:
        return '-'
    return html.escape(text, quote=True)


def _markdown_heading(value):
    """格式化 Markdown 章节标题，去掉富文本并保持可搜索的纯文本。"""
    return _label_text(value) or '未命名领域'


def _get_node_positions(node):
    """获取节点岗位数据，优先使用树查询中预取的岗位列表。"""
    positions = getattr(node, 'position_list', None)
    if positions is not None:
        return list(positions)
    return list(
        node.positions.filter(is_deleted=False)
        .prefetch_related('users')
        .order_by('-sort')
    )


def _format_position_name(position):
    """格式化岗位名称，岗位在导出表格中需要加粗。"""
    if not position:
        return '-'
    return f"<strong>{_html_label(position.name)}</strong>"


def _format_position_users(position):
    """格式化岗位人员，人员姓名在导出表格中需要加粗。"""
    if not position:
        return '-'
    users = list(position.users.all())
    if not users:
        return '-'
    names = []
    for user in users:
        display_name = _html_label(user.name or user.username)
        names.append(f"<strong>{display_name}</strong>")
    return '、'.join(names)


def _build_position_rows(positions):
    """将岗位列表转换为表格行，空岗位也保留一行占位。"""
    position_list = list(positions or [])
    if not position_list:
        return [{'position': None}]
    return [{'position': position} for position in position_list]


def _collect_descendant_groups(node, path: list[str]):
    """收集三级及更深节点，四级后续层级会拼接进三级节点名称中。"""
    groups = [
        {
            'third_name': ' / '.join(
                _label_text(part) for part in path if _label_text(part)
            ) or '-',
            'description': node.description,
            'rows': _build_position_rows(_get_node_positions(node)),
        }
    ]
    for child in getattr(node, 'child_list', []):
        groups.extend(_collect_descendant_groups(child, [*path, child.name]))
    return groups


def _build_second_groups(second_node):
    """构建二级节点下的表格分组，二级自身岗位作为三级为空的一组。"""
    groups = []
    direct_positions = _get_node_positions(second_node)
    if direct_positions:
        groups.append(
            {
                'third_name': '-',
                'description': second_node.description,
                'rows': _build_position_rows(direct_positions),
            }
        )

    for child in getattr(second_node, 'child_list', []):
        groups.extend(_collect_descendant_groups(child, [child.name]))

    if not groups:
        groups.append(
            {
                'third_name': '-',
                'description': second_node.description,
                'rows': _build_position_rows([]),
            }
        )
    return groups


def _rowspan_attr(count: int):
    """按行数生成 HTML rowspan 属性，单行时不输出冗余属性。"""
    return f' rowspan="{count}"' if count > 1 else ''


def _build_domain_table(domain_node):
    """构建单个一级领域下的 HTML 表格。"""
    second_nodes = list(getattr(domain_node, 'child_list', []))
    lines = [
        '<table>',
        '<thead>',
        '<tr><th>二级节点</th><th>三级节点</th><th>岗位</th><th>人员</th><th>描述</th></tr>',
        '</thead>',
        '<tbody>',
    ]

    if not second_nodes:
        lines.append('<tr><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>')
    for second_node in second_nodes:
        groups = _build_second_groups(second_node)
        second_rowspan = sum(len(group['rows']) for group in groups)
        first_second_row = True

        for group in groups:
            group_rowspan = len(group['rows'])
            first_group_row = True
            for row in group['rows']:
                cells = []
                if first_second_row:
                    cells.append(
                        f'<td{_rowspan_attr(second_rowspan)}>{_html_label(second_node.name)}</td>'
                    )
                    first_second_row = False
                if first_group_row:
                    cells.append(
                        f'<td{_rowspan_attr(group_rowspan)}>{_html_label(group["third_name"])}</td>'
                    )
                cells.append(f'<td>{_format_position_name(row["position"])}</td>')
                cells.append(f'<td>{_format_position_users(row["position"])}</td>')
                if first_group_row:
                    cells.append(
                        f'<td{_rowspan_attr(group_rowspan)}>{_html_cell(group["description"])}</td>'
                    )
                    first_group_row = False
                lines.append('<tr>' + ''.join(cells) + '</tr>')

    lines.extend(['</tbody>', '</table>'])
    return '\n'.join(lines)


def _format_current_time(fmt: str):
    """格式化当前时间，兼容项目关闭 USE_TZ 时的 naive datetime。"""
    current = timezone.now()
    if not timezone.is_naive(current):
        current = timezone.localtime(current)
    return current.strftime(fmt)


def build_delivery_matrix_markdown():
    """构建沟通矩阵 Markdown 导出内容。"""
    roots = get_tree_data()
    lines = ['# 沟通矩阵', '']
    if not roots:
        lines.append('暂无沟通矩阵数据。')
        lines.append('')
        return '\n'.join(lines)

    for domain in roots:
        lines.extend(
            [
                f'## {_markdown_heading(domain.name)}',
                '',
                _build_domain_table(domain),
                '',
            ]
        )
    lines.append('')
    return '\n'.join(lines)


def export_delivery_matrix_markdown():
    """导出沟通矩阵 Markdown 文件响应。"""
    markdown = build_delivery_matrix_markdown()
    filename = _format_current_time('delivery-matrix-%Y%m%d%H%M%S.md')
    response = HttpResponse(markdown, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@transaction.atomic
def create_node(request, data: OrgNodeCreate):
    data_dict = data.dict()
    positions_data = data_dict.pop('positions', [])
    
    # Handle parent
    if data_dict.get('parent_id') == "":
         data_dict['parent_id'] = None
    
    # Handle linked_project
    if data_dict.get('linked_project_id') == "":
        data_dict['linked_project_id'] = None
    
    node = fu_crud.create(request, data_dict, OrganizationNode)
    
    # 创建节点时同步创建岗位，避免首次保存后岗位为空。
    for pos in positions_data:
        p_dict = _normalize_position_payload(pos)
        user_ids = p_dict.pop('user_ids', [])
        position = PositionStaff.objects.create(node=node, **p_dict)
        if user_ids:
            position.users.set(user_ids)

    _notify_config_changed_on_commit(
        request,
        'create_node',
        {'node_id': str(node.id), 'node_name': node.name},
    )
    return node

@transaction.atomic
def update_node(request, node_id, data: OrgNodeUpdate):
    data_dict = data.dict(exclude_unset=True)
    positions_data = data_dict.pop('positions', None)
    if 'parent_id' in data_dict:
         if data_dict['parent_id'] == "":
             data_dict['parent_id'] = None
         elif str(data_dict['parent_id']) == str(node_id):
             from ninja.errors import HttpError
             raise HttpError(400, "不能将节点自身设为父节点")
    
    if 'linked_project_id' in data_dict and data_dict['linked_project_id'] == "":
        data_dict['linked_project_id'] = None
         
    node = get_object_or_404(OrganizationNode, id=node_id)
    node = fu_crud.update(request, node_id, data_dict, OrganizationNode)
    if positions_data is not None:
        # 编辑节点接口支持一次性保存基础信息与岗位，避免前端产生两次配置变更通知。
        _replace_node_positions(node, positions_data)

    _notify_config_changed_on_commit(
        request,
        'update_node',
        {'node_id': str(node.id), 'node_name': node.name},
    )
    return node

@transaction.atomic
def delete_node(request, node_id):
    """删除组织节点（软删除）"""
    node = get_object_or_404(OrganizationNode, id=node_id)
    
    # 检查是否有子节点
    if node.children.exists():
        from ninja.errors import HttpError
        raise HttpError(400, "该节点存在子节点，无法删除")
    
    fu_crud.delete(node_id, OrganizationNode)
    _notify_config_changed_on_commit(
        request,
        'delete_node',
        {'node_id': str(node_id), 'node_name': node.name},
    )
    return {"id": str(node_id)}

@transaction.atomic
def update_node_positions(request, node_id, positions: list[PositionStaffCreate]):
    node = get_object_or_404(OrganizationNode, id=node_id)
    result = _replace_node_positions(node, positions)
    _notify_config_changed_on_commit(
        request,
        'update_positions',
        {'node_id': str(node.id), 'node_name': node.name},
    )
    return result

def get_tree_data():
    """获取组织架构树数据"""
    # 预取岗位与用户，保证根节点等场景返回最新岗位数据
    positions_qs = PositionStaff.objects.filter(is_deleted=False).prefetch_related('users').order_by('-sort')

    nodes = OrganizationNode.objects.prefetch_related(
        Prefetch('positions', queryset=positions_qs, to_attr='position_list'),
        'linked_project',
        'linked_project__milestone',
    ).order_by('-sort_order', 'sys_create_datetime')
    
    # Build tree in memory
    node_map = {n.id: n for n in nodes}
    roots = []
    
    # Initialize child_list for all nodes
    for node in nodes:
        node.child_list = []
        
    # Build parent-child relationships
    for node in nodes:
        if node.parent_id:
            parent = node_map.get(node.parent_id)
            if parent:
                parent.child_list.append(node)
            else:
                # Orphan node, treat as root
                roots.append(node)
        else:
            # Root node
            roots.append(node)
            
    return roots

def get_valid_parent_tree(node_id: str = None):
    """获取可用父节点树（排除当前节点及其子树）"""
    # 复用 get_tree_data 的查询逻辑
    positions_qs = PositionStaff.objects.filter(is_deleted=False).prefetch_related('users').order_by('-sort')

    nodes = OrganizationNode.objects.prefetch_related(
        Prefetch('positions', queryset=positions_qs, to_attr='position_list'),
        'linked_project',
        'linked_project__milestone',
    ).order_by('-sort_order', 'sys_create_datetime')
    
    # 1. Build full tree in memory
    node_map = {str(n.id): n for n in nodes}
    roots = []
    
    for node in nodes:
        node.child_list = []
        
    for node in nodes:
        if node.parent_id:
            parent = node_map.get(str(node.parent_id))
            if parent:
                parent.child_list.append(node)
            else:
                roots.append(node)
        else:
            roots.append(node)
            
    # 2. If no node_id, return full tree
    if not node_id:
        return roots

    # 3. Identify forbidden nodes (target node and its descendants)
    forbidden_ids = set()
    if node_id in node_map:
        target = node_map[node_id]
        # BFS to find all descendants
        stack = [target]
        while stack:
            curr = stack.pop()
            forbidden_ids.add(str(curr.id))
            stack.extend(curr.child_list)
            
    # 4. Filter the tree
    # Helper to filter children recursively
    def filter_children(node_list):
        result = []
        for node in node_list:
            if str(node.id) in forbidden_ids:
                continue
            # Recursively filter children
            node.child_list = filter_children(node.child_list)
            result.append(node)
        return result

    return filter_children(roots)
