from celery import shared_task, current_task
from .processing import generate_descriptions

@shared_task(bind=True)
def generate_descriptions_task(self, csv_path, images_folder_path):
    # Assuming you have some loop here that processes each description
    for i, item in enumerate(items_to_process, start=1):
        # Update task state with progress
        self.update_state(state='PROGRESS', meta={'current': i, 'total': len(items_to_process)})
        # Your processing logic here

    return generate_descriptions(csv_path, images_folder_path)


