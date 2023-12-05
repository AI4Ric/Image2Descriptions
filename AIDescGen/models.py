from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings

def user_directory_path(instance, filename):
    # This function generates a path to save each user's files: "media/user_<id>/<filename>"
    # 'instance' is an instance of the model where the FileField is defined.
    # 'filename' is the original name of the uploaded file.

    # You could add further directory structuring here, such as including the date.
    upload_date = instance.timestamp.strftime('%Y%m%d')
    return os.path.join(f'user_{instance.user.id}', upload_date, filename)

class UserUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100)
    file = models.FileField(upload_to=user_directory_path)
    folder_name = models.CharField(max_length=255, default='default_folder_name', editable=False)
    task_id = models.CharField(max_length=255, blank=True, null=True)
    csv_file_name = models.CharField(max_length=255, blank=True, null=True)   
    
    def get_download_url(self):
        # Return the URL to download the file
        return self.file.url
    
    def delete(self, *args, **kwargs):
        self.file.delete(save=False)  # Delete the file
        super(UserUpload, self).delete(*args, **kwargs)

        
