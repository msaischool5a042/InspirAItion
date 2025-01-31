from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from azure.storage.blob import BlobServiceClient
from django.conf import settings

from app.forms import PostForm
from app.models import Post


@login_required
def index(request: HttpRequest) -> HttpResponse:
    qs = Post.objects.all()
    return render(request, "app/index.html", {"posts": qs})


def post_detail(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    return render(request, "app/post_detail.html", {"post": post})

@login_required
def create_post(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            if request.FILES.get("image"):
                file = request.FILES["image"]
                file_name = f"{file.name}"

                # Azure Blob Storage 설정
                blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_CONNECTION_STRING
                )
                container_name = settings.CONTAINER_NAME
                blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=file_name
                )

                # 파일 업로드
                blob_client.upload_blob(file, overwrite=True)

                # 파일 URL 생성
                file_url = blob_client.url
                post.image = file_url

            post.save()
            return redirect("/app/")
    else:
        form = PostForm()
    return render(request, "app/create_post.html", {"form": form})

@login_required
def edit_post(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            if request.FILES.get("image"):
                file = request.FILES["image"]
                file_name = f"{file.name}"

                # Azure Blob Storage 설정
                blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_CONNECTION_STRING
                )
                container_name = settings.CONTAINER_NAME
                blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=file_name
                )

                # 파일 업로드
                blob_client.upload_blob(file, overwrite=True)

                # 파일 URL 생성
                file_url = blob_client.url
                post.image = file_url

            post.save()
            return redirect("/app/")
    else:
        form = PostForm(instance=post)
    return render(request, "app/edit_post.html", {"form": form, "post": post})

@login_required
def delete_post(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        post.delete()
        return redirect("/app/")
    return render(request, "app/post_detail.html", {"post": post})