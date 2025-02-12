from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("posts/new/", views.create_post, name="create_post"),
    path("posts/<int:pk>/", views.post_detail, name="post_detail"),
    path("posts/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("posts/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("ai/generate/", views.generate_image, name="generate_image"),
    path("gallery/my/", views.my_gallery, name="my_gallery"),
    path("gallery/public/", views.public_gallery, name="public_gallery"),
    path(
        "posts/<int:post_id>/comments/",
        views.comment_list_create,
        name="comment_list_create",
    ),
    path("comments/<int:pk>/", views.comment_detail, name="comment_detail"),
    # 임시 추가 경로
    path(
        "custom-admin/", views.custom_admin, name="custom_admin"
    ),  # 커스텀 관리자 페이지 경로 설정
    path("home/", views.home, name="home"),  # 홈 페이지 경로 설정
    path("services/", views.services, name="services"),  # Services 페이지 경로 설정
    path("our_team/", views.our_team, name="our_team"),  # Our Team 페이지 경로 설정
    path("board/", views.board, name="board"),  # Board 페이지 경로 설정
    path("about/", views.about, name="about"),  # About 페이지 경로 설정
    path("ai_play/", views.ai_play, name="ai_play"),
    path("art_gal/", views.art_gal, name="art_gal"),
    path("send/", views.send_email, name="send_email"),
    path("email_list/", views.email_list, name="email_list"),
    path("email_detail/<int:email_id>/", views.email_detail, name="email_detail"),
    path("read_caption/", views.read_caption, name="read_caption"),
]
