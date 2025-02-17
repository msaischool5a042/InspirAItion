from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from azure.storage.blob import BlobServiceClient
import logging
from urllib.parse import urlparse


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    image = models.URLField(blank=True, null=True, max_length=1000)
    generated_prompt = models.TextField(blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    tags = models.JSONField(blank=True, null=True)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        if self.image:
            try:
                blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_CONNECTION_STRING
                )
                container_client = blob_service_client.get_container_client(
                    settings.CONTAINER_NAME
                )

                blob_name = urlparse(self.image).path.split("/")[-1]

                container_client.delete_blob(blob_name)
                logging.info(f"Blob {blob_name} deleted successfully")

            except Exception as e:
                logging.error(f"Error deleting blob: {str(e)}")

        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and not isinstance(self.image, str):
            self.image_url = self.image.url

    @property
    def author_nickname(self):
        return (
            self.user.profile.nickname
            if hasattr(self.user, "profile")
            else self.user.username
        )


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"

    @property
    def author_nickname(self):
        return (
            self.author.profile.nickname
            if hasattr(self.author, "profile")
            else self.author.username
        )


class AIGeneration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.TextField()
    generated_prompt = models.TextField()
    image_url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s image - {self.created_at}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI 생성 이미지"
        verbose_name_plural = "AI 생성 이미지들"


class TagUsage(models.Model):
    tag = models.CharField(max_length=100, unique=True)
    count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.tag} : {self.count}"


# class Tag(models.Model):
#     name = models.CharField(max_length=100, unique=True)

#     def __str__(self):
#         return self.name
