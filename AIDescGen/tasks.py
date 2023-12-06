# In tasks.py
from celery import shared_task
from .processing import generate_descriptions

@shared_task(bind=True)
def generate_descriptions_task(self, csv_path, images_folder_path):
    def update_progress(current, total):
        progress_percent = int((current / total) * 100)
        self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': progress_percent})

    result = generate_descriptions(csv_path, images_folder_path, progress_callback=update_progress)
    return result

