from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view),
    path('login/', views.login_view),
    path('logout/', views.logout_view),
    path('me/', views.me_view),

    # 服务器
    path('servers/', views.ServerViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('servers/<int:pk>/', views.ServerViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
    path('servers/join/', views.ServerViewSet.as_view({'post': 'join_server'})),
    path('servers/<int:pk>/members/', views.ServerViewSet.as_view({'get': 'members'})),
    path('servers/<int:pk>/leave/', views.ServerViewSet.as_view({'post': 'leave_server'})),
    path('servers/<int:pk>/online/', views.ServerViewSet.as_view({'get': 'online_members'})),

    # 频道
    path('servers/<int:server_pk>/channels/',
         views.ChannelViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('servers/<int:server_pk>/channels/<int:pk>/',
         views.ChannelViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})),

    # 消息
    path('channels/<int:channel_pk>/messages/',
         views.MessageViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('channels/<int:channel_pk>/messages/<int:pk>/',
         views.MessageViewSet.as_view({'delete': 'destroy'})),

    # 私信
    path('users/search/', views.search_users),
    path('dm/', views.dm_conversations),
    path('dm/<int:user_id>/', views.dm_messages),
]
