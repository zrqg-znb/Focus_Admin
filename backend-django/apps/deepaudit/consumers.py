from __future__ import annotations

from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentTask
from apps.deepaudit.permissions import require_project_role
from apps.deepaudit.realtime import task_group_name
from core.user.user_model import User
from core.websocket.consumers import TokenAuthWebSocketConsumer


class DeepAuditTaskConsumer(TokenAuthWebSocketConsumer):
    async def connect(self):
        await super().connect()
        if not hasattr(self, 'user_id'):
            return
        self.task_id = self.scope.get('url_route', {}).get('kwargs', {}).get('task_id', '')
        allowed = await sync_to_async(self._check_access)()
        if not allowed:
            await self.close(code=4003)
            return
        await self.channel_layer.group_add(task_group_name(self.task_id), self.channel_name)
        await self.send_message('deepaudit_ready', 'DeepAudit 任务流已连接', {'task_id': self.task_id})

    async def disconnect(self, close_code):
        if getattr(self, 'task_id', ''):
            await self.channel_layer.group_discard(task_group_name(self.task_id), self.channel_name)
        await super().disconnect(close_code)

    def _check_access(self) -> bool:
        user = User.objects.filter(id=getattr(self, 'user_id', '')).first()
        task = AgentTask.objects.select_related('project').filter(id=getattr(self, 'task_id', ''), is_deleted=False).first()
        if not user or not task:
            return False
        require_project_role(user, task.project, min_role='viewer')
        self.user = user
        self.task = task
        return True

    async def handle_message(self, data):
        message_type = data.get('type', 'unknown')
        if message_type in {'subscribe', 'resume'}:
            await self.send_message('subscribed', '已订阅 DeepAudit 任务事件', {'task_id': self.task_id})
            return
        await self.send_message('deepaudit_ack', f'已收到消息类型: {message_type}', {'task_id': self.task_id})

    async def deepaudit_task_event(self, event):
        payload = event.get('payload') or {}
        await self.send_message('deepaudit_event', payload.get('message') or 'DeepAudit 任务事件', payload)
