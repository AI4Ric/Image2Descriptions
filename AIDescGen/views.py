import re
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
import os
from datetime import datetime
from django.conf import settings
from .models import UserUpload
import zipfile
from django.http import HttpResponse


@login_required
def file_upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('image_files')
        if files:
            # Create a timestamped folder for the upload
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            user_folder = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}', 'images', timestamp)

            # Create the user-specific and timestamped directories if they don't exist
            os.makedirs(user_folder, exist_ok=True)

            for file in files:
                fs = FileSystemStorage(location=user_folder)
                filename = fs.save(file.name, file)
                file_url = fs.url(filename)

            user_upload = UserUpload(user=request.user, file=os.path.join(timestamp, filename))
            user_upload.save()

            # Redirect or inform the user of successful upload
            return HttpResponseRedirect(reverse('home'))

    # Your code to handle GET requests or show the form
    return render(request, 'AIDescGen/home.html')

@login_required
def user_files(request):
    # Assuming you have a model that tracks file uploads with fields like 'timestamp' and 'status'
    uploads = UserUpload.objects.filter(user=request.user).order_by('-timestamp')
    print(uploads)

    for upload in uploads:
        upload.display_timestamp = upload.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'AIDescGen/user_files.html', {'user_files': uploads})