# api/urls.py


from django.urls import path
from .finance_views import (
    FinanceSummaryView, FinancePaymentsView, FinanceDebtView, 
    FinanceChartView, FinanceExpenseView
)
from .ai_views import AIAssistantView # AI viewni albatta qo'shing
from .views import (
    # Auth
    LoginView, LogoutView, MeView, RegisterView, 
    ChangePasswordView, PasswordResetRequestView,
    # Dashboard
    DashboardView,
    # Clients
    ClientListCreateView, ClientDetailView, ClientArchiveView,
    # Categories & Products
    CategoryListCreateView, CategoryDetailView,
    ProductListCreateView, ProductDetailView,
    # Orders
    OrderListCreateView, OrderDetailView, OrderStatusUpdateView, 
    OrderPaymentLinkView, OrderContractView, PaymentCreateView,
    # Warehouse
    StockListView, StockUpdateView, StockMovementListCreateView,
    # Messages
    MessageListCreateView, MessageDetailView, MessageMarkAllReadView,
    # Users
    UserListView, UserDetailView, UserToggleActiveView, UserResetPasswordView,
)
from apps.notifications.views import (
    NotificationListView, NotificationMarkReadView, NotificationClearView,
)
from .client_views import ClientDashboardView, ClientCatalogView, ClientOrderCreateView


urlpatterns = [
    # ── AUTH ──────────────────────────────────────────────────────────
    path('auth/login/',           LoginView.as_view(),          name='api-login'),
    path('auth/logout/',          LogoutView.as_view(),         name='api-logout'),
    path('auth/me/',              MeView.as_view(),             name='api-me'),
    path('auth/register/',        RegisterView.as_view(),       name='api-register'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='api-change-password'),
    path('auth/forgot-password/', PasswordResetRequestView.as_view(), name='api-forgot-password'),

    # ── DASHBOARD ─────────────────────────────────────────────────────
    path('dashboard/', DashboardView.as_view(), name='api-dashboard'),

    # ── CLIENTS ───────────────────────────────────────────────────────
    path('clients/',                  ClientListCreateView.as_view(), name='api-clients'),
    path('clients/<int:pk>/',         ClientDetailView.as_view(),     name='api-client-detail'),
    path('clients/<int:pk>/archive/', ClientArchiveView.as_view(),    name='api-client-archive'),

    # ── CATEGORIES ────────────────────────────────────────────────────
    path('categories/',          CategoryListCreateView.as_view(), name='api-categories'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(),     name='api-category-detail'),

    # ── PRODUCTS ──────────────────────────────────────────────────────
    path('products/',          ProductListCreateView.as_view(), name='api-products'),
    path('products/<int:pk>/', ProductDetailView.as_view(),     name='api-product-detail'),

    # ── ORDERS ────────────────────────────────────────────────────────
    path('orders/',                          OrderListCreateView.as_view(),  name='api-orders'),
    path('orders/<int:pk>/',                 OrderDetailView.as_view(),      name='api-order-detail'),
    path('orders/<int:pk>/status/',          OrderStatusUpdateView.as_view(),name='api-order-status'),
    path('orders/<int:pk>/pay/',             OrderPaymentLinkView.as_view(), name='api-order-pay'),
    path('orders/<int:pk>/contract/',        OrderContractView.as_view(),    name='api-order-contract'),
    path('orders/<int:order_pk>/payments/',  PaymentCreateView.as_view(),    name='api-payment-create'),

    # ── WAREHOUSE ─────────────────────────────────────────────────────
    path('stock/',               StockListView.as_view(),              name='api-stock'),
    path('stock/<int:pk>/',      StockUpdateView.as_view(),            name='api-stock-update'),
    path('movements/',           StockMovementListCreateView.as_view(),name='api-movements'),
    # AI
    path('ai/', AIAssistantView.as_view(), name='api-ai'),

    # ── CLIENT PORTAL ─────────────────────────────────────────────────
    path('client/dashboard/', ClientDashboardView.as_view(), name='api-client-dashboard'),
    path('client/catalog/',   ClientCatalogView.as_view(),   name='api-client-catalog'),
    path('client/order/',     ClientOrderCreateView.as_view(), name='api-client-order'),

    path('finance/summary/',  FinanceSummaryView.as_view(),  name='api-finance-summary'),
    path('finance/payments/', FinancePaymentsView.as_view(), name='api-finance-payments'),
    path('finance/debts/',    FinanceDebtView.as_view(),    name='api-finance-debts'),
    path('finance/chart/',    FinanceChartView.as_view(),    name='api-finance-chart'),
    path('finance/expenses/', FinanceExpenseView.as_view(),  name='api-finance-expenses'),
    # ── MESSAGES ──────────────────────────────────────────────────────
    path('messages/',              MessageListCreateView.as_view(),  name='api-messages'),
    path('messages/<int:pk>/',     MessageDetailView.as_view(),      name='api-message-detail'),
    path('messages/read-all/',     MessageMarkAllReadView.as_view(), name='api-messages-read-all'),

    # ── USERS ─────────────────────────────────────────────────────────
    path('users/',                        UserListView.as_view(),         name='api-users'),
    path('users/<int:pk>/',               UserDetailView.as_view(),       name='api-user-detail'),
    path('users/<int:pk>/toggle-active/', UserToggleActiveView.as_view(), name='api-user-toggle'),
    path('users/<int:pk>/reset-password/',UserResetPasswordView.as_view(),name='api-user-reset-pwd'),

    # ── NOTIFICATIONS (REST Fallback) ─────────────────────────────────
    path('notifications/',        NotificationListView.as_view(),     name='api-notif-list'),
    path('notifications/read/',   NotificationMarkReadView.as_view(), name='api-notif-read'),
    path('notifications/clear/',  NotificationClearView.as_view(),    name='api-notif-clear'),
]