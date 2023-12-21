from celery import shared_task
from .processing import generate_descriptions, preprocess_images
from .models import UserUpload
from django.utils import timezone

@shared_task(bind=True)
def generate_descriptions_task(self, upload_id, csv_file_key, images_folder_path):
    # Update start time
    upload = UserUpload.objects.get(id=upload_id)
    upload.start_time = timezone.now()
    upload.save()

    def update_progress(current, total):
        progress_percent = int((current / total) * 100)
        self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': progress_percent})

    try:
        result = generate_descriptions(csv_file_key, images_folder_path, progress_callback=update_progress)
        
        # Update end time and status on success
        upload.end_time = timezone.now()
        upload.status = 'Completed'
        upload.save()

        return result
    except Exception as e:
        # Update status on failure
        upload.status = 'Failed'
        upload.save()
        raise e

@shared_task(bind=True)
def preprocess_images_task(self, upload_id, file_urls, include_vendor_no, include_category):
    # Update start time
    upload = UserUpload.objects.get(id=upload_id)
    user_directory = upload.folder_name

    def update_progress(current, total):
        progress_percent = int((current / total) * 100)
        self.update_state(state='ImagesProcessing', meta={'current': current, 'total': total, 'percent': progress_percent})

    try:
        df = preprocess_images(file_urls, include_vendor_no, include_category, user_directory, progress_callback=update_progress)
        return df
    except Exception as e:
        # Update status on failure
        upload.status = 'Failed'
        upload.save()
        raise e