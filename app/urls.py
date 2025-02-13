from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    # AI Playground
    path("create/", views.create_post, name="create_post"),
    path("ai/generate/", views.generate_image, name="generate_image"),
    # Artwork
    path("artwork/my/", views.my_gallery, name="my_gallery"),
    path("artwork/public/", views.public_gallery, name="public_gallery"),
    # Post Detail & Comments
    path("posts/<int:pk>/", views.post_detail, name="post_detail"),
    path("posts/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("posts/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path(
        "posts/<int:post_id>/comments/",
        views.comment_list_create,
        name="comment_list_create",
    ),
    path("comments/<int:pk>/", views.comment_detail, name="comment_detail"),
    path(
        "posts/<int:pk>/generate_curation/",
        views.generate_curation,
        name="generate_curation",
    ),
    # 추가: read_text 뷰 URL 패턴
    path("read_text/", views.read_text, name="read_text"),
]
