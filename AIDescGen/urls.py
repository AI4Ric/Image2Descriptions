from django.urls import path
from . import views

urlpatterns = [
    path('', views.file_upload, name='home'),
    path('user-files/', views.user_files, name='user_files'),
]
