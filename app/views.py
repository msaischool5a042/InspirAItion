import os
import re
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from azure.storage.blob import BlobServiceClient
from django.conf import settings
from openai import AzureOpenAI
import requests
import uuid
import json
from datetime import datetime

from util.common.azure_computer_vision import get_image_caption_and_tags
from util.common.azure_speech import synthesize_text_to_speech
from django.views.decorators.http import require_GET

from .forms import PostWithAIForm, PostEditForm
from .models import Post, AIGeneration, Comment, TagUsage  # TagUsage 추가

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("ai_generation.log"), logging.StreamHandler()],
)

GPT_CLIENT = AzureOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    api_key=settings.AZURE_OPENAI_API_KEY,
    api_version=settings.AZURE_OPENAI_API_VERSION,
)

DALLE_CLIENT = AzureOpenAI(
    azure_endpoint=settings.AZURE_DALLE_ENDPOINT,
    api_key=settings.AZURE_DALLE_API_KEY,
    api_version=settings.AZURE_DALLE_API_VERSION,
)


GPT_CLIENT_o3 = AzureOpenAI(
    azure_endpoint=settings.AZURE_3OMINI_ENDPOINT,
    api_key=settings.AZURE_3OMINI_API_KEY,
    api_version=settings.AZURE_3OMINI_API_VERSION,
)


def generate_prompt_with_gpt3o(user_input):
    try:
        print("GPT-3o-mini를 사용해 프롬프트를 생성합니다...")

        # JSON 파일에서 프롬프트 로드
        dalle_prompt = load_json_prompt("ai_playground/dalle_o3_prompt.json")

        response = GPT_CLIENT_o3.chat.completions.create(
            model="team6-o3-mini",
            messages=[
                dalle_prompt,
                {"role": "user", "content": user_input},
            ],
        )

        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            print("응답을 생성하지 못했습니다.")
            return None

    except Exception as e:
        print("GPT-3o-mini 호출 중 예외 발생:", str(e))
        return None


def generate_prompt_with_gpt4o(user_input):
    """GPT-4o를 사용해 DALL-E 3 프롬프트 생성"""
    try:
        logging.info("GPT-4o를 사용해 프롬프트를 생성합니다...")

        # JSON 파일에서 프롬프트 로드
        dalle_prompt = load_json_prompt("ai_playground/dalle_prompt.json")

        response = GPT_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[
                dalle_prompt,
                {"role": "user", "content": user_input},
            ],
            temperature=0.7,
        )

        if response.choices and len(response.choices) > 0:
            generated_prompt = response.choices[0].message.content.strip()
            logging.info(f"생성된 프롬프트: {generated_prompt}")
            return generated_prompt
        return None

    except Exception as e:
        logging.error(f"GPT-4o 호출 중 예외 발생: {str(e)}", exc_info=True)
        return None


def save_image_to_blob(image_url, prompt, user_id):
    """이미지를 Azure Blob Storage에 저장"""
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        sanitised_prompt = re.sub(r'[<>:"/\\|?*]', "", prompt[:20]).strip()
        filename = f"user_{user_id}_{timestamp}_{unique_id}_{sanitised_prompt}.png"

        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_CONNECTION_STRING
        )
        blob_client = blob_service_client.get_blob_client(
            container=settings.CONTAINER_NAME, blob=filename
        )

        blob_client.upload_blob(response.content, overwrite=True)
        logging.info(f"이미지가 Blob Storage에 저장되었습니다: {filename}")
        return blob_client.url

    except Exception as e:
        logging.error(f"Blob Storage 저장 중 오류 발생: {str(e)}", exc_info=True)
        return None


def generate_image_with_dalle(prompt):
    """DALL-E를 사용해 이미지를 생성"""
    try:
        logging.info("DALL-E를 사용해 이미지를 생성합니다...")

        result = DALLE_CLIENT.images.generate(model="dall-e-3", prompt=prompt, n=1)

        if result and result.data:
            image_url = result.data[0].url
            logging.info(f"DALL-E 호출 성공! 생성된 이미지 URL: {image_url}")
            return image_url
        return None

    except Exception as e:
        logging.error(f"DALL-E 호출 중 예외 발생: {str(e)}", exc_info=True)
        return None


@login_required
def generate_image(request):
    """이미지 생성 뷰"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    prompt = request.POST.get("prompt", "").strip()
    if not prompt:
        return JsonResponse({"error": "프롬프트를 입력해주세요."}, status=400)

    try:
        # generated_prompt = generate_prompt_with_gpt4o(prompt)
        generated_prompt = generate_prompt_with_gpt3o(prompt)
        if not generated_prompt:
            return JsonResponse({"error": "프롬프트 생성에 실패했습니다."}, status=500)

        image_url = generate_image_with_dalle(generated_prompt)
        if not image_url:
            return JsonResponse({"error": "이미지 생성에 실패했습니다."}, status=500)

        blob_url = save_image_to_blob(image_url, generated_prompt, request.user.id)
        if not blob_url:
            return JsonResponse({"error": "이미지 저장에 실패했습니다."}, status=500)

        return JsonResponse(
            {"image_url": blob_url, "generated_prompt": generated_prompt}
        )

    except Exception as e:
        logging.error(f"이미지 생성 중 오류 발생: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def read_text(request: HttpRequest) -> HttpResponse:
    try:
        data = json.loads(request.body)
        caption = data.get("caption", "").strip()
        if not caption:
            return JsonResponse({"error": "캡션이 제공되지 않았습니다."}, status=400)
        audio_data = synthesize_text_to_speech(caption)
        if not audio_data:
            raise Exception("음성 데이터를 생성하지 못했습니다.")
        response = HttpResponse(audio_data, content_type="audio/wav")
        response["Content-Disposition"] = 'attachment; filename="caption.wav"'
        return response
    except Exception as e:
        logging.error("read_text 에러", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def index(request: HttpRequest) -> HttpResponse:
    ai_images = None
    if request.user.is_authenticated:
        ai_images = AIGeneration.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:1]
    ai_images = None
    if request.user.is_authenticated:
        ai_images = AIGeneration.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:1]
    return render(request, "app/home.html", {"ai_images": ai_images})


@login_required
def post_detail(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post.objects.select_related("user__profile"), pk=pk)
    # 큐레이션 텍스트는 초기에는 빈 값으로 전달
    curation_text = ""

    previous_url = request.META.get("HTTP_REFERER", "home")
    logging.info(f"이전 화면의 주소: {previous_url}")

    return render(
        request,
        "app/post_detail.html",
        {
            "post": post,
            # "caption": caption[0] if caption else "",
            # "tags": ", ".join(tags),
            "curation_text": curation_text,
        },
    )


@login_required
@require_http_methods(["POST"])
def generate_curation(request, pk):
    post = get_object_or_404(Post.objects.select_related("user__profile"), pk=pk)
    caption = post.caption
    tags = post.tags

    caption_str = caption[0] if caption else ""
    try:
        data = json.loads(request.body)
        selected_style = data.get("style", "Emotional")
    except Exception:
        selected_style = "Emotional"

    # generate_ai_curation returns a dict with various style keys.
    curation_text = generate_ai_curation(
        selected_style, post.title, caption_str, ", ".join(tags)
    )
    return JsonResponse({"curation_text": curation_text})


def load_json_prompt(file_path="style_prompts.json"):
    """
    Load style prompts from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing style prompts.

    Returns:
        dict: A dictionary of styles and their respective prompts.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from the file {file_path}.")
        return {}


def generate_ai_curation(selected_style, user_prompt, captions, tags):
    """
    한글로 각 스타일별 큐레이션을 생성하는 함수

    Args:
        user_prompt (str): 사용자 프롬프트
        captions (str): 이미지 설명
        tags (str): 태그들

    Returns:
        dict: 한글 스타일명과 큐레이션을 담은 딕셔너리
    """
    # JSON 파일에서 스타일 프롬프트 로드
    style_prompts = load_json_prompt("ai_playground/style_prompts.json")

    combined_text = f"프롬프트: {user_prompt}\n이미지 설명: {captions}\n태그: {tags}"

    # 결과를 저장할 딕셔너리
    curations = {}

    # 선택된 스타일에 해당하는 큐레이션 생성
    style_prompt = style_prompts.get(selected_style, "")
    if style_prompt:
        try:
            response = GPT_CLIENT_o3.chat.completions.create(
                model="team6-o3-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an art curation expert. Provide a very detailed and professional analysis of the given work.
                        {style_prompt} The analysis should be written in a specific and persuasive manner,
                        and should clearly reveal the characteristics and value of the work from a professional perspective.
                        As an expert in evaluating artwork, please provide an assessment of the piece within 100 words, utilizing the provided information.
                        Please write a curation in Korean based on the following information.""",
                    },
                    {"role": "user", "content": combined_text},
                ],
            )
            curations[selected_style] = response.choices[0].message.content
        except Exception as e:
            curations[selected_style] = (
                f"Error generating {selected_style} curation: {str(e)}"
            )
    else:
        curations[selected_style] = "Invalid style selected."

    return curations[selected_style]


@login_required
def create_post(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PostWithAIForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user

            generated_image_url = request.POST.get("generated_image_url")
            generated_prompt = request.POST.get("generated_prompt")
            caption, tags = get_image_caption_and_tags(generated_image_url)

            if generated_image_url:
                blob_url = save_image_to_blob(
                    generated_image_url, form.cleaned_data["prompt"], request.user.id
                )
                if blob_url:
                    post.image = generated_image_url

                    AIGeneration.objects.create(
                        user=request.user,
                        prompt=form.cleaned_data["prompt"],
                        generated_prompt=generated_prompt,
                        image_url=blob_url,
                    )
            if generated_prompt:
                post.generated_prompt = generated_prompt
            if caption:
                post.caption = caption[0]
            if tags:
                # tags를 리스트 형태로 저장
                post.tags = tags

            post.save()
            form.save_m2m()

            # 분석된 tags 정보를 TagUsage 업데이트
            if tags:
                update_tag_usage_on_create(tags)

            return redirect("post_detail", pk=post.pk)
    else:
        form = PostWithAIForm()
    return render(request, "app/create_post.html", {"form": form})


def update_tag_usage_on_create(tags):
    if not isinstance(tags, list):
        return
    for tag in tags:
        tag_usage, created = TagUsage.objects.get_or_create(tag=tag)
        tag_usage.count += 1
        tag_usage.save()


def update_tag_usage_on_delete(tags):
    if not isinstance(tags, list):
        return
    for tag in tags:
        try:
            tag_usage = TagUsage.objects.get(tag=tag)
            if tag_usage.count > 0:
                tag_usage.count -= 1
                tag_usage.save()
        except TagUsage.DoesNotExist:
            continue


@login_required
def edit_post(request: HttpRequest, pk: int) -> HttpResponse:
    """게시물 수정 (이미지 수정 불가)"""
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = PostEditForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            # 수정: is_public 필드 업데이트 추가
            post.is_public = True if request.POST.get("is_public") else False
            post.save()
            return redirect("post_detail", pk=pk)
    else:
        form = PostEditForm(instance=post)
    return render(request, "app/edit_post.html", {"form": form, "post": post})


@login_required
def delete_post(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        previous_url = request.META.get("HTTP_REFERER", "home")
        logging.info(f"이전 화면의 주소: {previous_url}")
        if post.tags:
            update_tag_usage_on_delete(post.tags)
        post.delete()
        return redirect("public_gallery")
    return render(request, "app/post_detail.html", {"post": post})


@login_required
def my_gallery(request):
    search_query = request.GET.get("search", "")
    tag_filter = request.GET.get("tag", "")
    posts_qs = Post.objects.filter(user=request.user)
    if search_query:
        posts_qs = posts_qs.filter(title__icontains=search_query)
    # 태그 필터 적용: __contains 대신 파이썬 리스트 필터링 수행
    if tag_filter:
        all_posts = list(posts_qs.order_by("-date_posted"))
        posts_list = [
            post for post in all_posts if post.tags and tag_filter in post.tags
        ]
    else:
        posts_list = list(posts_qs.order_by("-date_posted"))

    page = int(request.GET.get("page", "1"))
    post_cnt = 9
    offset = (page - 1) * post_cnt
    total_count = len(posts_list)
    posts = posts_list[offset : offset + post_cnt]
    has_more = (offset + post_cnt) < total_count

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        posts_data = [
            {
                "id": post.id,
                "title": post.title,
                "image": post.image,
                "detail_url": f"/app/posts/{post.id}/",  # 변경됨: /post/ -> /app/posts/
                "content": post.content,
            }
            for post in posts
        ]
        return JsonResponse({"posts": posts_data, "has_more": has_more})

    top_tags = TagUsage.objects.order_by("-count")[:10]
    return render(
        request,
        "app/gallery.html",
        {
            "posts": posts,
            "gallery_type": "personal",
            "search_query": search_query,
            "top_tags": top_tags,
            "selected_tag": tag_filter,
            "has_more": has_more,  # 추가
        },
    )


def public_gallery(request):
    search_query = request.GET.get("search", "")
    tag_filter = request.GET.get("tag", "")
    page = int(request.GET.get("page", "1"))
    post_cnt = 9
    offset = (page - 1) * post_cnt

    posts_qs = Post.objects.filter(is_public=True)
    if search_query:
        posts_qs = posts_qs.filter(title__icontains=search_query)

    total_count = posts_qs.count()

    if tag_filter:
        # __contains 대신 파이썬 리스트 필터링 수행
        all_posts = list(posts_qs.order_by("date_posted"))
        posts_list = [
            post for post in all_posts if post.tags and tag_filter in post.tags
        ]
        posts = posts_list[offset : offset + post_cnt]
        total_count = len(posts_list)
    else:
        posts = posts_qs.order_by("date_posted")[offset : offset + post_cnt]

    has_more = (offset + post_cnt) < total_count

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        posts_data = [
            {
                "id": post.id,
                "title": post.title,
                "image": post.image,
                "detail_url": f"/app/posts/{post.id}/",  # 변경됨: /post/ -> /app/posts/
                "content": post.content,  # 추가: 내용 필드
            }
            for post in posts
        ]
        return JsonResponse({"posts": posts_data, "has_more": has_more})

    top_tags = TagUsage.objects.order_by("-count")[:10]
    return render(
        request,
        "app/gallery.html",
        {
            "posts": posts,
            "gallery_type": "public",
            "search_query": search_query,
            "top_tags": top_tags,
            "selected_tag": tag_filter,
            "has_more": has_more,  # 추가
        },
    )


@require_http_methods(["GET", "POST"])
def comment_list_create(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "GET":
        comments = Comment.objects.filter(post=post).select_related(
            "author", "author__profile"
        )
        data = [
            {
                "id": comment.id,
                "message": comment.message,
                "author": comment.author_nickname if comment.author else "Anonymous",
                "create_at": comment.created_at.isoformat(),
            }
            for comment in comments
        ]
        return JsonResponse({"comments": data})

    elif request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

        try:
            data = json.loads(request.body)
            message = data.get("message", "").strip()

            if not message:
                return JsonResponse({"error": "댓글 내용을 입력해주세요."}, status=400)

            comment = Comment.objects.create(
                post=post, author=request.user, message=message
            )

            return JsonResponse(
                {
                    "id": comment.id,
                    "message": comment.message,
                    "author": comment.author.username,
                    "created_at": comment.created_at.isoformat(),
                },
                status=201,
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 요청입니다."}, status=400)


@require_http_methods(["DELETE", "PATCH"])
def comment_detail(request, pk):
    comment = get_object_or_404(Comment, id=pk)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    if comment.author != request.user:
        return JsonResponse({"error": "권한이 없습니다."}, status=403)

    if request.method == "DELETE":
        comment.delete()
        return JsonResponse({"message": "댓글이 삭제되었습니다."})

    elif request.method == "PATCH":
        try:
            data = json.loads(request.body)
            message = data.get("message", "").strip()

            if not message:
                return JsonResponse({"error": "댓글 내용을 입력해주세요."}, status=400)

            comment.message = message
            comment.save()

            return JsonResponse(
                {
                    "id": comment.id,
                    "message": comment.message,
                    "author": comment.author.username,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat(),
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 요청입니다."}, status=400)


@login_required
def custom_admin(request):
    return redirect("admin")  # 관리자 페이지로 리디렉션


def home(request):
    return render(request, "app/home.html")


def about(request):
    return render(request, "app/about.html")


def services(request):
    return render(
        request, "app/services.html"
    )  # html정리 전(main 에는 about으로 연결해둠)


def our_team(request):
    return render(
        request, "app/our_team.html"
    )  # html정리 전(main 에는 about으로 연결해둠


def board(request):
    return render(request, "app/board.html")  # 새 게시판 앱 생성 예정


def contact_us(request):
    return render(request, "app/contact_us.html")  # email_app 연결 예정정


def ai_play(request):
    return render(request, "app/ai_play.html")  # html만 있고, 아직 기능 merge 전


def art_gal(request):
    """공개 갤러리"""
    search_query = request.GET.get("search", "")
    posts = Post.objects.filter(is_public=True)

    if search_query:
        posts = posts.filter(title__icontains=search_query)

    posts = posts.order_by("date_posted")
    search_query = request.GET.get("search", "")
    posts = Post.objects.filter(is_public=True)

    if search_query:
        posts = posts.filter(title__icontains=search_query)

    posts = posts.order_by("date_posted")
    return render(
        request,
        "app/artgal.html",
        {"posts": posts, "gallery_type": "public", "search_query": search_query},
    )


def index_ai(request):
    return render(request, "app/index_ai.html")


def send_email(request):
    return render(request, "email_app/send_email.html")


def email_list(request):
    return render(request, "email_app/email_list.html")


def email_detail(request, email_id):
    return render(request, "email_app/email_detail.html")


def fullscreen_gallery(request):
    """전체 화면 갤러리 뷰"""
    posts = (
        Post.objects.filter(is_public=True)
        .exclude(image__isnull=True)
        .exclude(image__exact="")
        .order_by("-date_posted")
    )

    return render(request, "app/fullscreen_gallery.html", {"posts": posts})
