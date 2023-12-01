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
    # Your fields like 'file', 'timestamp', 'status', etc.
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100)
    file = models.FileField(upload_to=user_directory_path)  # Define 'user_directory_path' function to set upload path
    
    def get_download_url(self):
        # Return the URL to download the file
        return self.file.url
