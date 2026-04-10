import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: ws://host/ws/notifications/
    Token autentifikatsiya: ?token=<DRF token>
    """

    async def connect(self):
        # Token orqali foydalanuvchini topamiz
        token = self._get_token()
        self.user = await self._get_user(token)

        if not self.user:
            await self.close(code=4001)
            return

        # Har user o'z guruhiga qo'shiladi: "user_<id>"
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Ulangandan so'ng o'qilmagan bildirishnomalar sonini yuboramiz
        count = await self._unread_count()
        await self.send(json.dumps({
            'type':         'connected',
            'unread_count': count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ── Client → Server xabarlari ──────────────────────────────────────────
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except Exception:
            return

        action = data.get('action')

        if action == 'mark_read':
            notif_id = data.get('id')
            await self._mark_read(notif_id)
            await self.send(json.dumps({'type': 'marked_read', 'id': notif_id}))

        elif action == 'mark_all_read':
            await self._mark_all_read()
            await self.send(json.dumps({'type': 'all_read'}))

        elif action == 'get_list':
            notifs = await self._get_notifications()
            await self.send(json.dumps({'type': 'list', 'notifications': notifs}))

    # ── Server → Client event handlerlari ─────────────────────────────────
    async def send_notification(self, event):
        """channel_layer.group_send() dan keladi"""
        await self.send(json.dumps({
            'type':         'notification',
            'notification': event['notification'],
        }))

    async def send_system(self, event):
        """Tizim xabarlari uchun"""
        await self.send(json.dumps({
            'type':    'system',
            'message': event.get('message', ''),
        }))

    # ── Yordamchi metodlar ─────────────────────────────────────────────────
    def _get_token(self):
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                return part[6:]
        # Header dan ham tekshiramiz
        headers = dict(self.scope.get('headers', []))
        auth = headers.get(b'authorization', b'').decode()
        if auth.startswith('Token '):
            return auth[6:]
        return None

    @database_sync_to_async
    def _get_user(self, token):
        if not token:
            return None
        try:
            from rest_framework.authtoken.models import Token
            tok = Token.objects.select_related('user').get(key=token)
            return tok.user if tok.user.is_active else None
        except Exception:
            return None

    @database_sync_to_async
    def _unread_count(self):
        from .models import Notification
        return Notification.objects.filter(recipient=self.user, is_read=False).count()

    @database_sync_to_async
    def _mark_read(self, notif_id):
        from .models import Notification
        if notif_id == 'all':
            Notification.objects.filter(recipient=self.user, is_read=False).update(is_read=True)
        else:
            Notification.objects.filter(pk=notif_id, recipient=self.user).update(is_read=True)

    @database_sync_to_async
    def _mark_all_read(self):
        from .models import Notification
        Notification.objects.filter(recipient=self.user, is_read=False).update(is_read=True)

    @database_sync_to_async
    def _get_notifications(self, limit=30):
        from .models import Notification
        return [n.to_dict() for n in
                Notification.objects.filter(recipient=self.user).order_by('-created_at')[:limit]]