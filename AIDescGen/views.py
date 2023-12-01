import re
import io
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
from django.views.decorators.http import require_POST


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

            user_upload = UserUpload(user=request.user, file=os.path.join(timestamp, filename),folder_name=timestamp)
            user_upload.save()

            # Redirect or inform the user of successful upload
            return HttpResponseRedirect(reverse('home'))

    # Your code to handle GET requests or show the form
    return render(request, 'AIDescGen/home.html')

@login_required
def user_files(request):
    # Assuming you have a model that tracks file uploads with fields like 'timestamp' and 'status'
    uploads = UserUpload.objects.filter(user=request.user).order_by('-timestamp')

    for upload in uploads:
        upload.display_timestamp = upload.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'AIDescGen/user_files.html', {'user_files': uploads})


@login_required
def download_files(request, folder_name):
    user_folder = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}', 'images', folder_name)

    # Create a zip file in memory
    zip_filename = f"{folder_name}.zip"
    s = io.BytesIO()
    with zipfile.ZipFile(s, 'w') as zip_file:
        for filename in os.listdir(user_folder):
            file_path = os.path.join(user_folder, filename)
            zip_file.write(file_path, filename)
    # Set the pointer to the start
    s.seek(0)

    # Create a HTTP response
    response = HttpResponse(s, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={zip_filename}'

    return response


@require_POST
@login_required
def delete_files(request):
    # Get the list of selected file IDs from the POST request
    file_ids = request.POST.getlist('file_ids')

    # Filter UserUpload instances by the current user and the selected file IDs
    uploads_to_delete = UserUpload.objects.filter(user=request.user, id__in=file_ids)

    # Delete the files and the database records
    for upload in uploads_to_delete:
        try:
            # This deletes the file from the filesystem
            upload.file.delete()
            # This deletes the database record
            upload.delete()
        except Exception as e:
            # If an error occurs during deletion, print the error message
            print(f"Error deleting file: {e}")

    return HttpResponseRedirect(reverse('user_files'))


import logging

logger = logging.getLogger(__name__)
