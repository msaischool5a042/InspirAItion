from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("posts/new/", views.create_post, name="create_post"),
    path("posts/<int:pk>/", views.post_detail, name="post_detail"),
    path("posts/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("posts/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("ai/generate/", views.generate_image, name="generate_image")
]
