from django.contrib import admin
from .models import UserUpload
from Image2Descriptions.celery import app 

@admin.register(UserUpload)
class UserUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'timestamp', 'status', 'file', 'folder_name', 'task_id', 'csv_file_name', 'start_time', 
                    'end_time', 'terminated_by', 'termination_reason', 'is_terminated')
    list_filter = ('status', 'user')
    search_fields = ('user__username', 'status')
    actions = ['terminate_tasks']

    def terminate_tasks(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "You do not have permission to terminate tasks.")
            return
        for upload in queryset:
            if upload.task_id:
                app.control.revoke(upload.task_id, terminate=True)
                upload.status = 'Terminated'
                upload.is_terminated = True
                upload.terminated_by = request.user  # Recording the user who terminated the task
                upload.save()
        self.message_user(request, "Selected tasks have been terminated.")
    terminate_tasks.short_description = 'Terminate selected tasks'
