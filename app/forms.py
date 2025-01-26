from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "tag_set", "image"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }
