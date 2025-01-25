from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView

from team6.settings import env
from .forms import UploadFileForm

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from accounts.forms import AccountForm
from accounts.models import Account


# Create your views here.
def index(request: HttpRequest) -> HttpResponse:
    qs = Account.objects.all()
    return render(request, "accounts/index.html", {"accounts": qs})


def account_detail(request: HttpRequest, pk: int) -> HttpResponse:
    # account = Account.objects.get(pk=pk)
    account = get_object_or_404(Account, pk=pk)
    return render(request, "accounts/account_detail.html", {"account": account})


account_new = CreateView.as_view(
    model=Account,
    form_class=AccountForm,
    success_url="/accounts/",
)


from urllib.parse import urljoin
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect
from .forms import UploadFileForm
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


from django.conf import settings
from azure.storage.blob import BlobServiceClient

def upload_file(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            if file:  # Ensure the file is not None
                file_name = f"{file.name}"  # Ensure the file name is not None

                # Azure Blob Storage 설정
                blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_CONNECTION_STRING)
                container_name = settings.CONTAINER_NAME
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)

                # 파일 업로드
                blob_client.upload_blob(file.read(), overwrite=True)

                # 파일 URL 생성
                file_url = blob_client.url
                print(f"File URL: {file_url}")
                return redirect("upload_success")
            else:
                print("Error: file is None")
    else:
        form = UploadFileForm()
    return render(request, "accounts/upload.html", {"form": form})


def upload_success(request):
    return render(request, "accounts/upload_success.html")
