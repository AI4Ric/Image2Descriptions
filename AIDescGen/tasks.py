from celery import shared_task
from .processing import generate_descriptions
from .models import UserUpload
from django.utils import timezone

@shared_task(bind=True)
def generate_descriptions_task(self, upload_id, csv_path, images_folder_path):
    # Update start time
    upload = UserUpload.objects.get(id=upload_id)
    upload.start_time = timezone.now()
    upload.save()

    def update_progress(current, total):
        progress_percent = int((current / total) * 100)
        self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': progress_percent})

    try:
        result = generate_descriptions(csv_path, images_folder_path, progress_callback=update_progress)
        
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

