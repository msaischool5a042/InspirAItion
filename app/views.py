from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from azure.storage.blob import BlobServiceClient
from django.conf import settings
from openai import AzureOpenAI

from .forms import PostForm
from .models import Post, AIGeneration

GPT_CLIENT = AzureOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    api_key=settings.AZURE_OPENAI_API_KEY,
    api_version=settings.AZURE_OPENAI_API_VERSION
)

DALLE_CLIENT = AzureOpenAI(
    azure_endpoint=settings.AZURE_DALLE_ENDPOINT,
    api_key=settings.AZURE_DALLE_API_KEY,
    api_version=settings.AZURE_DALLE_API_VERSION
)

@login_required
def index(request: HttpRequest) -> HttpResponse:
    posts = Post.objects.filter(user=request.user).order_by('-date_posted')
    ai_images = AIGeneration.objects.filter(user=request.user).order_by('-created_at')[:5]
    return render(request, "app/index.html", {
        "posts": posts,
        "ai_images": ai_images
    })


def post_detail(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    return render(request, "app/post_detail.html", {"post": post})


@login_required
def create_post(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if request.FILES.get("image"):
                file = request.FILES["image"]
                file_name = f"{file.name}"
                blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_CONNECTION_STRING
                )
                container_name = settings.CONTAINER_NAME
                blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=file_name
                )
                blob_client.upload_blob(file, overwrite=True)
                post.image = blob_client.url
            post.save()
            form.save_m2m()  # Save many-to-many relationships
            return redirect("index")
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
                blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_CONNECTION_STRING
                )
                container_name = settings.CONTAINER_NAME
                blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=file_name
                )
                blob_client.upload_blob(file, overwrite=True)
                post.image = blob_client.url
            post.save()
            form.save_m2m()
            return redirect("post_detail", pk=pk)
    else:
        form = PostForm(instance=post)
    return render(request, "app/edit_post.html", {"form": form, "post": post})


@login_required
def delete_post(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        post.delete()
        return redirect("index")
    return render(request, "app/post_detail.html", {"post": post})


@login_required
def generate_ai_image(request):
    context = {}
    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()
        if prompt:
            try:
                response = GPT_CLIENT.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "Create a detailed, creative visual prompt for DALL-E."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                generated_prompt = response.choices[0].message.content.strip()
                
                result = DALLE_CLIENT.images.generate(
                    model="dall-e-3",
                    prompt=generated_prompt,
                    n=1
                )
                
                image_url = result.data[0].url
                
                AIGeneration.objects.create(
                    user=request.user,
                    prompt=prompt,
                    generated_prompt=generated_prompt,
                    image_url=image_url
                )
                
                context['image_url'] = image_url
                context['generated_prompt'] = generated_prompt
                
            except Exception as e:
                context['error'] = str(e)
    
    return render(request, "app/generate_image.html", context)