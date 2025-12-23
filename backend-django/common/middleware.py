"""
日志 django中间件
"""
import json

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from core.models import OperationLog, User

from common.utils.request_util import (
    get_browser,
    get_os,
    get_request_data,
    get_request_ip,
    get_request_path,
    get_request_user,
    get_verbose_name,
)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    添加安全相关的 HTTP 头
    """
    
    def process_response(self, request, response):
        # 添加安全头
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy - 可根据实际需求调整
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        
        return response


class ApiLoggingMiddleware(MiddlewareMixin):
    """
    用于记录API访问日志中间件
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.enable = getattr(settings, 'API_LOG_ENABLE', None) or False
        self.methods = getattr(settings, 'API_LOG_METHODS', None) or set()

    @classmethod
    def __handle_request(cls, request):
        request.request_ip = get_request_ip(request)
        request.request_data = get_request_data(request)
        request.request_path = get_request_path(request)

    def __handle_response(self, request, response):
        body = getattr(request, 'request_data', {})
        # 请求含有password则用*替换掉
        if isinstance(body, dict) and body.get('password', ''):
            body = body.copy()
            body['password'] = '*' * len(body['password'])

        # 尝试解析响应内容
        response_data = {}
        try:
            if hasattr(response, 'data') and isinstance(response.data, dict):
                response_data = response.data
            elif hasattr(response, 'content'):
                response_data = json.loads(response.content.decode('utf-8'))
        except Exception:
            pass

        user = get_request_user(request)
        if not user:
            return

        # 判断状态 (2xx 为成功)
        status = 200 <= response.status_code < 300

        info = {
            'request_username': user.username if isinstance(user, User) else getattr(user, 'username', 'Unknown'),
            'request_ip': getattr(request, 'request_ip', 'unknown'),
            'sys_creator_id': user.id if isinstance(user, User) else getattr(user, 'id', None),
            'request_method': request.method,
            'request_path': request.request_path,
            'request_body': body,
            'response_code': response.status_code,
            'request_os': get_os(request),
            'request_browser': get_browser(request),
            'request_msg': request.session.get('request_msg'),
            'status': status,
            'json_result': response_data,
            'request_modular': settings.API_MODEL_MAP.get(request.path, ''),
        }

        # 如果 process_view 中创建了 log，这里进行更新；否则新建
        operation_log_id = getattr(request, 'operation_log_id', None)
        operation_log, created = OperationLog.objects.update_or_create(
            defaults=info, 
            id=operation_log_id
        )
        
        # 如果是新建且没有模块名，再次尝试匹配
        if not operation_log.request_modular and settings.API_MODEL_MAP.get(request.request_path, None):
            operation_log.request_modular = settings.API_MODEL_MAP[request.request_path]
            operation_log.save()

    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.enable:
            if self.methods == 'ALL' or request.method in self.methods:
                if hasattr(view_func, 'cls') and hasattr(view_func.cls, 'queryset'):
                    # 尝试预创建日志（可选，如果需要记录正在处理的状态）
                    # 注意：此时可能没有 user 信息，如果 user 是必填项，这里不能 save
                    # 由于 OperationLog 模型中 request_username 是必填项，这里跳过 save，
                    # 仅尝试提取模块名供 response 阶段使用
                    request.request_modular = get_verbose_name(view_func.cls.queryset)
        return None

    def process_request(self, request):
        self.__handle_request(request)

    def process_response(self, request, response):
        """
        主要请求处理完之后记录
        :param request:
        :param response:
        :return:
        """
        if self.enable:
            if self.methods == 'ALL' or request.method in self.methods:
                self.__handle_response(request, response)
        return response
