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
    text = html.unescape(strip_tags(str(value or '')))
    return re.sub(r'\s+', ' ', text).strip()


def _markdown_cell(value):
    """转义 Markdown 表格单元格，避免竖线和换行破坏表格结构。"""
    text = _plain_text(value)
    if not text:
        return '-'
    return text.replace('\\', '\\\\').replace('|', '\\|')


def _format_node_path(path: list[str]):
    """格式化节点层级路径。"""
    return ' / '.join(path) if path else '-'


def _format_position_staff(positions):
    """格式化岗位与人员，保持单元格信息密度。"""
    position_list = list(positions or [])
    if not position_list:
        return '-'

    fragments = []
    for position in position_list:
        users = list(position.users.all())
        user_names = '、'.join(
            _plain_text(user.name or user.username) for user in users
        )
        fragments.append(f"{_plain_text(position.name)}：{user_names or '-'}")
    return '；'.join(fragments) or '-'


def _walk_matrix_rows(nodes, path: list[str] | None = None, level: int = 1):
    """按树顺序展开沟通矩阵节点，生成 Markdown 表格行数据。"""
    rows = []
    current_path = path or []
    for node in nodes:
        node_path = [*current_path, _plain_text(node.name)]
        positions = getattr(node, 'position_list', None)
        if positions is None:
            positions = (
                node.positions.filter(is_deleted=False)
                .prefetch_related('users')
                .order_by('-sort')
            )
        linked_project = getattr(node, 'linked_project', None)
        rows.append(
            [
                _format_node_path(node_path),
                str(level),
                node.name,
                node.code,
                linked_project.name if linked_project else None,
                _format_position_staff(positions),
                node.description,
            ]
        )
        rows.extend(
            _walk_matrix_rows(getattr(node, 'child_list', []), node_path, level + 1)
        )
    return rows


def _collect_matrix_stats(nodes):
    """统计导出文件中的节点、岗位和去重人员数量。"""
    node_count = 0
    position_count = 0
    user_ids = set()
    stack = list(nodes or [])
    while stack:
        node = stack.pop()
        node_count += 1
        positions = getattr(node, 'position_list', [])
        position_count += len(positions)
        for position in positions:
            for user in position.users.all():
                user_ids.add(str(user.id))
        stack.extend(getattr(node, 'child_list', []))
    return node_count, position_count, len(user_ids)


def _format_current_time(fmt: str):
    """格式化当前时间，兼容项目关闭 USE_TZ 时的 naive datetime。"""
    current = timezone.now()
    if not timezone.is_naive(current):
        current = timezone.localtime(current)
    return current.strftime(fmt)


def build_delivery_matrix_markdown():
    """构建沟通矩阵 Markdown 导出内容。"""
    roots = get_tree_data()
    exported_at = _format_current_time('%Y-%m-%d %H:%M:%S')
    node_count, position_count, user_count = _collect_matrix_stats(roots)
    rows = _walk_matrix_rows(roots)

    lines = [
        '# 沟通矩阵',
        '',
        f'- 导出时间：{exported_at}',
        f'- 节点数量：{node_count}',
        f'- 岗位数量：{position_count}',
        f'- 人员数量：{user_count}',
        '',
        '| 层级路径 | 层级 | 节点名称 | 节点编码 | 关联项目 | 岗位人员 | 描述 |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]

    if rows:
        for row in rows:
            lines.append(
                '| ' + ' | '.join(_markdown_cell(cell) for cell in row) + ' |'
            )
    else:
        lines.append('| - | - | - | - | - | - | - |')

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
