"""
ASGI config for application project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')

# 初始化Django
django.setup()

# 初始化Django ASGI应用
django_asgi_app = get_asgi_application()

# 导入WebSocket路由（必须在django.setup()之后）
from core.websocket.routing import websocket_urlpatterns

# 配置ASGI应用程序以支持HTTP和WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
