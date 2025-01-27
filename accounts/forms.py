from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class SignUpForm(UserCreationForm):
    nickname = forms.CharField(
        max_length=50, 
        required=True, 
        help_text="사용하실 닉네임을 입력해주세요.",
        widget=forms.TextInput(attrs={'placeholder': '닉네임'}))

    class Meta:
        model = User
        fields = ("username", "nickname", "password1", "password2")
