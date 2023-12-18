import re
import io
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
import os
from datetime import datetime
from django.conf import settings
from .models import UserUpload
import zipfile
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_POST
from .processing import create_dataframe, generate_descriptions
from .tasks import generate_descriptions_task
from celery.result import AsyncResult
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from PIL import Image, ExifTags
import posixpath
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'AIDescGen/login.html', {
                'error': 'Invalid username or password.'
            })
    else:
        return render(request, 'AIDescGen/login.html')



@login_required
def file_upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('image_files')
        include_vendor_no = 'include_vendor_no' in request.POST
        include_category = 'include_category' in request.POST

        # Determine the regex pattern based on user selection
        if include_vendor_no and include_category:
            regex_pattern = r'^(\d+)_(\d+)_(\w+)_?.*\.jpg$'
        elif include_vendor_no or include_category:
            regex_pattern = r'^(\d+)_(\d+|\w+)_?.*\.jpg$'
        else:
            regex_pattern = r'^(\d+)(_?.*)?\.jpg$'

        # Check each file for correct format before processing    
        for file in files:
            if not re.match(regex_pattern, file.name.lower()):
                error_message = "File naming format is incorrect based on your selections."
                return render(request, 'AIDescGen/home.html', {'error_message': error_message})
            
        if files:
            # Create a timestamped folder for the upload
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            user_folder = posixpath.join(f'user_{request.user.id}', 'images', timestamp)

            file_paths = []
            for file in files:
                file_key = posixpath.join(user_folder, file.name)

                if not default_storage.exists(file_key):
                    default_storage.save(file_key, file)
                    file_paths.append(default_storage.url(file_key))
                    print(f"Uploaded file to S3: {file_key}")

            user_upload = UserUpload(user=request.user, status='Initializing', file=file_key,folder_name=timestamp)
            user_upload.save()

            df = create_dataframe(file_paths, include_vendor_no, include_category)

            # Check if dataframe creation was successful
            if isinstance(df, str):
                # Handle the case where no valid files were processed
                return render(request, 'AIDescGen/home.html', {'error_message': df})
            
            # Save the dataframe to a CSV file in the user's documents directory
            documents_folder = posixpath.join(f'user_{request.user.id}', 'documents', timestamp)
            csv_file_key = posixpath.join(documents_folder, f"{timestamp}_data.csv")

            csv_content = df.to_csv(index=False)
            default_storage.save(csv_file_key, ContentFile(csv_content))
            user_upload.csv_file_name = default_storage.url(csv_file_key)
            user_upload.save()

            # Cell generate_descriptions function
            upload_id = user_upload.id
            print(file_key)
            print(user_folder)

            task = generate_descriptions_task.delay(upload_id, csv_file_key, user_folder)
            user_upload.task_id = task.id  # Save the Celery task ID to the upload record
            user_upload.save()

            # Redirect or inform the user of successful upload
            success_message = "Your files are being processed. Please check the status on the progress page."
            return render(request, 'AIDescGen/home.html', {'success_message': success_message})

    # Your code to handle GET requests or show the form
    return render(request, 'AIDescGen/home.html')

@login_required
def user_files(request):
    uploads = UserUpload.objects.filter(user=request.user).order_by('-timestamp')

    for upload in uploads:
        upload.display_timestamp = upload.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'AIDescGen/user_files.html', {'user_files': uploads})

def resize_and_orient_image(image_path, max_size=2500):
    with Image.open(image_path) as img:
        # Correct orientation according to EXIF data
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = dict(img._getexif().items())

            if exif[orientation] == 3:
                img = img.rotate(180, expand=True)
            elif exif[orientation] == 6:
                img = img.rotate(270, expand=True)
            elif exif[orientation] == 8:
                img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # Cases: image doesn't have getexif, orientation is not in exif
            pass

        # Calculate the new size, maintaining the aspect ratio
        ratio = min(max_size / img.size[0], max_size / img.size[1])
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))

        # Resize the image
        resized_img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save the resized image to a temporary file
        temp_path = os.path.join(os.path.dirname(image_path), 'temp_' + os.path.basename(image_path))
        resized_img.save(temp_path)
        return temp_path, lambda: os.remove(temp_path) 


@login_required
def download_files(request, folder_name):
    user_folder = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}', 'images', folder_name)
    image_files = sorted([f for f in os.listdir(user_folder) if f.lower().endswith('.jpg')])

    # Define max images per zip and initialize counters
    max_images_per_zip = 48  # For example
    zip_count = 0
    images_in_current_zip = 0

    # Create a main zip file in memory if packaging all zips into one
    main_zip_memory = io.BytesIO()
    with zipfile.ZipFile(main_zip_memory, 'w') as main_zip:

        # Temporary storage for current batch of images
        current_zip_memory = io.BytesIO()
        current_zip = zipfile.ZipFile(current_zip_memory, 'w') 

        for filename in image_files:
            file_path = os.path.join(user_folder, filename)
            resized_path, cleanup = resize_and_orient_image(file_path)
            current_zip.write(resized_path, filename)
            cleanup() 

            images_in_current_zip += 1
            if images_in_current_zip >= max_images_per_zip:
                # Save current zip and start a new one
                current_zip.close()  # Make sure to close the current zip
                if zip_count == 0:
                    zip_filename = "images.zip"
                else:
                    zip_filename = f"images_{zip_count}.zip"
                main_zip.writestr(zip_filename, current_zip_memory.getvalue())

                # Reset for the next batch
                current_zip_memory = io.BytesIO()
                current_zip = zipfile.ZipFile(current_zip_memory, 'w')
                images_in_current_zip = 0
                zip_count += 1

        # Save the last zip if it has any images
        if images_in_current_zip > 0:
            current_zip.close()  # Make sure to close the last zip
            if zip_count == 0:
                zip_filename = "images.zip"
            else:
                zip_filename = f"images_{zip_count}.zip"
            main_zip.writestr(zip_filename, current_zip_memory.getvalue())

    # Set the pointer to the start of the main zip
    main_zip_memory.seek(0)

    # Create a HTTP response with the main zip file
    response = HttpResponse(main_zip_memory, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{folder_name}_images.zip"'

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

    csv_file_key = upload.csv_file_name

    # Check if the file exists in S3 and open it
    if default_storage.exists(csv_file_key):
        with default_storage.open(csv_file_key, 'rb') as csv_file:
            response = HttpResponse(csv_file, content_type='text/csv')
            # Set the content disposition header to prompt for download
            response['Content-Disposition'] = f'attachment; filename="result.csv"'
            return response
    else:
        raise Http404("CSV file not found.")

import logging

logger = logging.getLogger(__name__)
