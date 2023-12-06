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
from .processing import create_dataframe, generate_descriptions
from .tasks import generate_descriptions_task
from celery.result import AsyncResult
from django.http import JsonResponse
from django.shortcuts import get_object_or_404





@login_required
def file_upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('image_files')

        # Check each file for correct format before processing
        for file in files:
            if not re.match(r'^\d+_\d+_.+\.jpg$', file.name.lower()):
                error_message = "Files must be in the format 'lotNumber_vendorNumber_Something Else.jpg'."
                return render(request, 'AIDescGen/home.html', {'error_message': error_message})
            
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

            file_paths = [os.path.join(user_folder, file.name) for file in files]
            df = create_dataframe(file_paths)

            # Check if dataframe creation was successful
            if isinstance(df, str):
                # Handle the case where no valid files were processed
                return render(request, 'AIDescGen/home.html', {'error_message': df})
            
            # Save the dataframe to a CSV file in the user's documents directory
            documents_folder = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}', 'documents')
            os.makedirs(documents_folder, exist_ok=True)  # Create the directory if it doesn't exist
            csv_filename = os.path.join(documents_folder, f"{timestamp}_data.csv")
            df.to_csv(csv_filename, index=False)
            user_upload.csv_file_name = csv_filename
            user_upload.save()

            # Cell generate_descriptions function
            task = generate_descriptions_task.delay(csv_filename, user_folder)
            user_upload.task_id = task.id  # Save the Celery task ID to the upload record
            user_upload.save()

            # Redirect or inform the user of successful upload
            success_message = "Your files are being processed. Please check the status on the progress page."
            return render(request, 'AIDescGen/home.html', {'success_message': success_message})

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

def get_task_status(request, task_id):
    task_result = AsyncResult(task_id)
    status = "Completed" if task_result.status == "SUCCESS" else task_result.status
    response_data = {
        'status': status,
        'result': task_result.result if task_result.result else {}
    }
    return JsonResponse(response_data)

@login_required
def download_csv(request, task_id):
    # Retrieve the UserUpload object based on the task_id
    upload = get_object_or_404(UserUpload, task_id=task_id, user=request.user)

    # Define the path to the CSV file
    csv_file_path = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}', 'documents', upload.csv_file_name)

    # Open the file for reading
    with open(csv_file_path, 'rb') as csv_file:
        response = HttpResponse(csv_file, content_type='text/csv')
        # Set the content disposition header to prompt for download
        response['Content-Disposition'] = f'attachment; filename="result.csv"'
        return response

import logging

logger = logging.getLogger(__name__)
