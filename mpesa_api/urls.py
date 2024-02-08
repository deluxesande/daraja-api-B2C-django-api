from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('stk-push-callback/', views.STKPushCallBack.as_view(), name='stk_push_callback'),
    path('status/', views.MpesaExpressStatusView.as_view(), name='stk_push_status'),
]