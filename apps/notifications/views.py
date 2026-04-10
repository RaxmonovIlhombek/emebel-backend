from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification


class NotificationListView(APIView):
    """GET /api/notifications/ — oxirgi 50 ta bildirishnoma"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:50]
        return Response([n.to_dict() for n in notifs])


class NotificationMarkReadView(APIView):
    """POST /api/notifications/read/  body: {id: <int|'all'>}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notif_id = request.data.get('id')
        if notif_id == 'all':
            Notification.objects.filter(
                recipient=request.user, is_read=False
            ).update(is_read=True)
        else:
            Notification.objects.filter(
                pk=notif_id, recipient=request.user
            ).update(is_read=True)
        unread = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({'ok': True, 'unread_count': unread})


class NotificationClearView(APIView):
    """DELETE /api/notifications/clear/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        Notification.objects.filter(recipient=request.user).delete()
        return Response({'ok': True})