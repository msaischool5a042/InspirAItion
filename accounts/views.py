from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404

from accounts.models import Account


# Create your views here.
def index(request: HttpRequest) -> HttpResponse:
    qs = Account.objects.all()
    return render(request, "accounts/index.html", {"accounts": qs})


def account_detail(request: HttpRequest, pk: int) -> HttpResponse:
    # account = Account.objects.get(pk=pk)
    account = get_object_or_404(Account, pk=pk)
    return render(request, "accounts/account_detail.html", {"account": account})
