from django.urls import path
from . import views

app_name = 'board'

urlpatterns = [
    # 페이지
    path('', views.board_list, name='list'),
    path('write/', views.post_write, name='write'),
    path('<int:post_id>/edit/', views.post_write, name='edit'),  # 수정 페이지
    path('<int:post_id>/', views.post_detail, name='detail'),
    
    # 게시글 API
    path('api/posts/', views.api_posts, name='api_posts'),
    path('api/create/', views.post_create, name='create'),
    path('api/<int:post_id>/update/', views.post_update, name='update'),
    path('api/<int:post_id>/delete/', views.post_delete, name='delete'),
    path('api/<int:post_id>/check_password/', views.check_password, name='check_password'),
    
    # 댓글 API
    path('api/<int:post_id>/comment/', views.comment_create, name='comment_create'),
    path('api/comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),
]

