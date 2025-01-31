from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.create_post, name="create_post"),
    path("<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/delete/", views.delete_post, name="delete_post")
]
