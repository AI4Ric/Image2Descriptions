from django.urls import path
from . import views

urlpatterns = [
    path('', views.file_upload, name='home'),
    path('user-files/', views.user_files, name='user_files'),
    path('download/<str:folder_name>/', views.download_files, name='download_files'),
    path('delete-files/', views.delete_files, name='delete_files'),
    path('get-task-status/<task_id>/', views.get_task_status, name='get_task_status'),
    path('download-csv/<str:task_id>/', views.download_csv, name='download_csv'),
]
