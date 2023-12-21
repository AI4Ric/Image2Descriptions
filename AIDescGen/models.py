from django.db import models
from django.contrib.auth.models import User
#import os
import posixpath
from django.conf import settings

def user_directory_path(instance, filename):
    # This function generates a path to save each user's files: "media/user_<id>/<filename>"
    # 'instance' is an instance of the model where the FileField is defined.
    # 'filename' is the original name of the uploaded file.
    upload_date = instance.timestamp.strftime('%Y%m%d')
    #return os.path.join(f'user_{instance.user.id}', upload_date, filename)
    return posixpath.join(f'user_{instance.user.id}', upload_date, filename)

class UserUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100)
    file = models.FileField(upload_to=user_directory_path)
    folder_name = models.CharField(max_length=255, default='default_folder_name', editable=False)
    task_id = models.CharField(max_length=255, blank=True, null=True)
    csv_file_name = models.CharField(max_length=255, blank=True, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    terminated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='terminated_uploads')
    termination_reason = models.TextField(blank=True, null=True)
    is_terminated = models.BooleanField(default=False)   
    
    def get_download_url(self):
        # Return the URL to download the file
        return self.file.url
    
    def delete(self, *args, **kwargs):
        self.file.delete(save=False)  # Delete the file
        super().delete(*args, **kwargs)
        #super(UserUpload, self).delete(*args, **kwargs)

        
