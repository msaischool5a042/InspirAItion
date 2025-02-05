from django import forms
from .models import Post


# class PostForm(forms.ModelForm):
#     class Meta:
#         model = Post
#         fields = ["title", "content", "tag_set", "image"]
#         widgets = {
#             "image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
#         }

class PostWithAIForm(forms.ModelForm):
    prompt = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text='AI 이미지 생성을 위한 프롬프트'
    )

    class Meta:
        model = Post
        fields = ["title", "content", "tag_set"]

class PostEditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "tag_set"]