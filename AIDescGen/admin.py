from django.contrib import admin
from .models import UserUpload

@admin.register(UserUpload)
class UserUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'folder_name', 'task_id', 'csv_file_name')