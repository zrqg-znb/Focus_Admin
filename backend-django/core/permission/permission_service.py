#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Permission Service - 权限生成服务
从 Django Ninja Router 自动扫描 API 并生成权限
"""
import hashlib
import logging
import re
from typing import List, Dict, Tuple
from django.db.models import Q
from core.permission.permission_model import Permission
from core.menu.menu_model import Menu
from common.fu_cache import PermissionCacheManager

logger = logging.getLogger(__name__)


class PermissionGenerator:
    """权限生成器 - 从 API 路由自动生成权限"""

    METHOD_OPERATION_MAP = {
        'DELETE': 'delete',
        'GET': 'read',
        'PATCH': 'update',
        'POST': 'create',
        'PUT': 'update',
    }
    ACTION_ALIASES = {
        'bind': 'bind',
        'cancel': 'cancel',
        'checkpoints': 'checkpoints',
        'clear': 'clear',
        'close': 'close',
        'debug': 'debug',
        'detail': 'detail',
        'draft': 'draft',
        'events': 'events',
        'export': 'export',
        'failure_modes': 'failure_modes',
        'findings': 'findings',
        'history': 'history',
        'import': 'import',
        'issues': 'issues',
        'logs': 'logs',
        'options': 'options',
        'purge': 'purge',
        'query': 'query',
        'quick_create': 'quick_create',
        'reassign': 'reassign',
        'rebuild': 'rebuild',
        'recall': 'recall',
        'reject': 'reject',
        'reset': 'reset',
        'restore': 'restore',
        'resume': 'resume',
        'save': 'save',
        'scan': 'scan',
        'search': 'query',
        'set_default': 'set_default',
        'stats': 'stats',
        'status': 'status',
        'submit': 'submit',
        'summary': 'summary',
        'test': 'test',
        'toggle': 'toggle',
        'tree': 'tree',
        'upload': 'upload',
        'validate': 'validate',
        'zip': 'zip',
    }
    PLACEHOLDER_RE = re.compile(r'^\{(.+)\}$')

    @classmethod
    def sanitize_code_segment(cls, value: str) -> str:
        value = (value or '').strip().lower()
        if not value:
            return ''
        value = value.replace('-', '_').replace('.', '_').replace(' ', '_')
        if value.startswith(':'):
            value = value.removeprefix(':')
        match = cls.PLACEHOLDER_RE.match(value)
        if match:
            value = f"by_{match.group(1)}"
        value = re.sub(r'[^a-z0-9_]+', '_', value)
        value = re.sub(r'_+', '_', value).strip('_')
        return value

    @classmethod
    def is_path_parameter(cls, segment: str) -> bool:
        segment = (segment or '').strip()
        return bool(segment.startswith(':') or cls.PLACEHOLDER_RE.match(segment))

    @classmethod
    def split_api_path(cls, path: str) -> list[str]:
        parts = [item for item in (path or '').split('/') if item]
        if parts and parts[0] == 'api':
            parts = parts[1:]
        return parts

    @classmethod
    def resolve_operation(cls, path: str, method: str) -> str:
        parts = cls.split_api_path(path)
        static_parts = [
            cls.sanitize_code_segment(item) for item in parts if not cls.is_path_parameter(item)
        ]
        last_raw = parts[-1] if parts else ''
        last_static = static_parts[-1] if static_parts else ''
        method = (method or 'GET').upper()

        if method == 'GET':
            if cls.is_path_parameter(last_raw):
                return 'detail'
            return cls.ACTION_ALIASES.get(last_static, 'read')
        if method == 'POST':
            if parts and not cls.is_path_parameter(last_raw) and len(static_parts) > 1:
                return cls.ACTION_ALIASES.get(last_static, 'create')
            return 'create'
        if method in {'PUT', 'PATCH'}:
            if parts and not cls.is_path_parameter(last_raw) and len(static_parts) > 1:
                action = cls.ACTION_ALIASES.get(last_static, last_static or 'update')
                return f"update_{action}" if action not in {'update'} else 'update'
            return 'update'
        if method == 'DELETE':
            if parts and not cls.is_path_parameter(last_raw) and len(static_parts) > 1:
                action = cls.ACTION_ALIASES.get(last_static, last_static or 'delete')
                return f"delete_{action}" if action not in {'delete'} else 'delete'
            return 'delete'
        return cls.METHOD_OPERATION_MAP.get(method, 'access')

    @classmethod
    def build_permission_code(cls, path: str, method: str) -> str:
        parts = cls.split_api_path(path)
        static_parts = [
            cls.sanitize_code_segment(item) for item in parts if not cls.is_path_parameter(item)
        ]
        static_parts = [item for item in static_parts if item]

        domain = static_parts[0] if static_parts else 'api'
        operation = cls.resolve_operation(path, method)
        context_parts = static_parts[1:]
        if context_parts and cls.ACTION_ALIASES.get(context_parts[-1], context_parts[-1]) == operation:
            context_parts = context_parts[:-1]

        base_segments = [domain]
        if context_parts:
            base_segments.append('_'.join(context_parts))
        base_segments.append(operation)
        code = ':'.join(filter(None, base_segments))
        return cls.ensure_code_length(code, path, method)

    @classmethod
    def ensure_code_length(cls, code: str, path: str, method: str) -> str:
        max_length = Permission.CODE_MAX_LENGTH
        if len(code) <= max_length:
            return code

        parts = cls.split_api_path(path)
        static_parts = [
            cls.sanitize_code_segment(item) for item in parts if not cls.is_path_parameter(item)
        ]
        static_parts = [item for item in static_parts if item]
        domain = static_parts[0] if static_parts else 'api'
        operation = cls.resolve_operation(path, method)
        context_parts = static_parts[1:]

        compact_context = '_'.join(part[:8] for part in context_parts if part)
        compact_code = ':'.join(filter(None, [domain, compact_context, operation]))
        if len(compact_code) <= max_length:
            return compact_code

        digest = hashlib.md5(f'{method}:{path}'.encode('utf-8')).hexdigest()[:8]
        fallback = ':'.join(filter(None, [domain, operation, digest]))
        if len(fallback) <= max_length:
            return fallback

        return fallback[:max_length]

    @classmethod
    def normalize_submitted_code(
        cls,
        code: str | None,
        *,
        path: str,
        method: str,
    ) -> str:
        normalized = ':'.join(
            filter(
                None,
                [
                    cls.sanitize_code_segment(part)
                    for part in str(code or '').split(':')
                ],
            ),
        )
        if not normalized:
            normalized = cls.build_permission_code(path, method)
        return cls.ensure_code_length(normalized, path, method)

    @classmethod
    def validate_code_length(cls, code: str):
        max_length = Permission.CODE_MAX_LENGTH
        if len(code) > max_length:
            raise ValueError(f'权限编码过长，最长 {max_length} 个字符')

    @staticmethod
    def extract_api_info(path: str, method: str) -> Tuple[str, str]:
        """
        从 API 路径提取菜单编码和权限编码
        
        示例：
        - /api/core/user -> menu_code: 'user', perm_code: 'user:read'
        - /api/core/user (POST) -> menu_code: 'user', perm_code: 'user:create'
        """
        parts = PermissionGenerator.split_api_path(path)
        static_parts = [
            PermissionGenerator.sanitize_code_segment(item)
            for item in parts
            if not PermissionGenerator.is_path_parameter(item)
        ]
        static_parts = [item for item in static_parts if item]
        menu_code = static_parts[0] if static_parts else 'unknown'
        perm_code = PermissionGenerator.build_permission_code(path, method)
        return menu_code, perm_code
    
    @staticmethod
    def get_all_routes_from_ninja_api(api_instance) -> List[Dict]:
        """
        从 NinjaAPI 实例获取所有已注册的路由
        
        返回格式：
        [
            {
                'path': '/api/core/user',
                'method': 'GET',
                'operation_id': 'list_user',
                'summary': '获取用户列表'
            }
        ]
        """
        routes = []
        
        try:
            # 方法1：通过 get_openapi_schema 获取 OpenAPI 规范（最可靠）
            if hasattr(api_instance, 'get_openapi_schema'):
                try:
                    schema = api_instance.get_openapi_schema()
                    if schema and 'paths' in schema:
                        for path, path_item in schema['paths'].items():
                            for method, operation in path_item.items():
                                if method in ['get', 'post', 'put', 'delete', 'patch']:
                                    routes.append({
                                        'path': path,
                                        'method': method.upper(),
                                        'operation_id': operation.get('operationId', ''),
                                        'summary': operation.get('summary', ''),
                                    })
                    logger.info(f"通过 OpenAPI schema 获取到 {len(routes)} 个路由")
                    return routes
                except Exception as e:
                    logger.warning(f"通过 OpenAPI schema 获取路由失败: {str(e)}")
            
            # 方法2：访问 NinjaAPI 的 _routers 属性
            if hasattr(api_instance, '_routers'):
                for router in api_instance._routers:
                    if hasattr(router, 'path_operations'):
                        for path, operations in router.path_operations.items():
                            for operation in operations:
                                routes.append({
                                    'path': path,
                                    'method': operation.methods[0] if operation.methods else 'GET',
                                    'operation_id': getattr(operation, 'operation_id', ''),
                                    'summary': getattr(operation, 'summary', ''),
                                })
                if routes:
                    logger.info(f"通过 _routers 获取到 {len(routes)} 个路由")
                    return routes
            
            # 方法3：尝试访问 _operations 属性
            if hasattr(api_instance, '_operations'):
                for operation in api_instance._operations:
                    if hasattr(operation, 'path') and hasattr(operation, 'methods'):
                        routes.append({
                            'path': operation.path,
                            'method': operation.methods[0] if operation.methods else 'GET',
                            'operation_id': getattr(operation, 'operation_id', ''),
                            'summary': getattr(operation, 'summary', ''),
                        })
                if routes:
                    logger.info(f"通过 _operations 获取到 {len(routes)} 个路由")
                    return routes
            
            logger.warning("无法从 NinjaAPI 获取路由信息")
            
        except Exception as e:
            logger.error(f"获取路由失败: {str(e)}")
        
        return routes
    
    @staticmethod
    def auto_generate_permissions(api_instance, dry_run: bool = False) -> Dict:
        """
        自动生成权限
        
        Args:
            api_instance: NinjaAPI 实例
            dry_run: 如果为 True，只返回将要生成的权限，不实际创建
        
        Returns:
            {
                'created': 10,
                'skipped': 5,
                'failed': 0,
                'permissions': [...]
            }
        """
        routes = PermissionGenerator.get_all_routes_from_ninja_api(api_instance)
        
        created_count = 0
        skipped_count = 0
        failed_count = 0
        permissions_data = []
        
        for route in routes:
            try:
                menu_code, perm_code = PermissionGenerator.extract_api_info(
                    route['path'], 
                    route['method']
                )
                
                # 查找对应的菜单
                menu = (
                    Menu.objects.filter(
                        Q(authCode=menu_code)
                        | Q(authCode=menu_code.replace('_', '-'))
                        | Q(path__icontains=f"/{menu_code.replace('_', '-')}")
                    )
                    .order_by('order', 'sys_create_datetime')
                    .first()
                )
                if not menu:
                    logger.warning(f"菜单 {menu_code} 不存在，跳过权限 {perm_code}")
                    skipped_count += 1
                    continue
                
                # 检查权限是否已存在
                exists = Permission.objects.filter(
                    menu_id=menu.id,
                    code=perm_code
                ).exists()
                
                if exists:
                    skipped_count += 1
                    continue
                
                # 获取 HTTP 方法编码
                http_method_map = {
                    'GET': 0,
                    'POST': 1,
                    'PUT': 2,
                    'DELETE': 3,
                    'PATCH': 4,
                }
                http_method = http_method_map.get(route['method'].upper(), 0)

                # 获取权限类型名称
                operation = perm_code.split(':')[1]
                operation_names = {
                    'create': 'create',
                    'read': 'read',
                    'update': 'update',
                    'delete': 'delete',
                    'access': 'access',
                }
                operation_name = operation_names.get(operation, operation)
                
                perm_data = {
                    'menu_id': menu.id,
                    'name': f"{menu.name}{operation_name}",
                    'code': perm_code,
                    'permission_type': 1,  # API权限
                    'api_path': route['path'],
                    'http_method': http_method,
                    'description': route['summary'] or f"{menu.name}{operation_name}权限",
                    'is_active': True,
                }
                
                if not dry_run:
                    Permission.objects.create(**perm_data)
                    created_count += 1
                    logger.info(f"创建权限: {perm_code}")
                else:
                    created_count += 1
                
                permissions_data.append(perm_data)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"生成权限失败: {str(e)}")
        
        # 清除缓存
        if created_count > 0 and not dry_run:
            PermissionCacheManager.invalidate_permission_cache()
        
        return {
            'created': created_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'permissions': permissions_data,
        }
