from django.urls import path
from .views_click import ClickCallbackView
from .views_payme import PaymeCallbackView

urlpatterns = [
    path('click/prepare/', ClickCallbackView.as_view(), name='click-prepare'),
    path('click/complete/', ClickCallbackView.as_view(), name='click-complete'),
    path('payme/', PaymeCallbackView.as_view(), name='payme-callback'),
]
