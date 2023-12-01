import re
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
import os
from datetime import datetime
from django.conf import settings

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
                fs.save(file.name, file)
                # file_url = fs.url(filename) # If you need the URL of saved files

            # Redirect or inform the user of successful upload
            return HttpResponseRedirect(reverse('home'))

    # Your code to handle GET requests or show the form
    return render(request, 'AIDescGen/home.html')