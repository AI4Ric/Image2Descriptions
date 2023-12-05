document.addEventListener('DOMContentLoaded', function () {
    // Assuming each upload has a data attribute 'data-task-id' in your HTML
    const uploads = document.querySelectorAll('[data-task-id]');

    uploads.forEach(upload => {
        const taskId = upload.dataset.taskId;
        const statusElement = document.querySelector(`#status-${taskId}`);
        const progressBarElement = document.querySelector(`#progress-bar-${taskId}`);

        // Function to update progress
        const updateProgress = () => {
            fetch(`/get-task-status/${taskId}/`) // Adjust URL based on your `urls.py`
                .then(response => response.json())
                .then(data => {
                    if (statusElement) {
                        statusElement.innerText = data.status;
                    }
                    let progress = 0;
                    if (data.status === 'PROGRESS' && data.result) {
                        progress = data.result.progress; // Assuming 'progress' is part of your task result
                    } else if (data.status === 'SUCCESS') {
                        progress = 100;
                    }
                    if (progressBarElement) {
                        progressBarElement.style.width = progress + '%';
                    }
                })
                .catch(error => console.error('Error:', error));
        };

        setInterval(updateProgress, 2000); // Update progress every 2 seconds
    });
});
