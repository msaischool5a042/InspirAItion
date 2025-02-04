from django.urls import path
from . import views

app_name = 'ai_playground'

urlpatterns = [
    path('generate/', views.generate_image, name='generate_image'),
    path('history/', views.image_history, name='image_history')
]