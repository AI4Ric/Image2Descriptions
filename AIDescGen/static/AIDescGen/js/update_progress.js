document.addEventListener('DOMContentLoaded', function () {
    const uploads = document.querySelectorAll('[data-task-id]');

    uploads.forEach(upload => {
        const taskId = upload.dataset.taskId;
        const statusElement = document.getElementById(`status-${taskId}`);
        const progressBarElement = document.getElementById(`progress-bar-${taskId}`);
        const downloadElement = document.getElementById(`download-${taskId}`); // Assuming you have an element with this ID for download links

        const updateProgress = () => {
            fetch(`/get-task-status/${taskId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === "Completed") {
                        // When the task is completed, hide the progress bar and show the download link
                        if (progressBarElement) {
                            progressBarElement.style.display = 'none';
                        }
                        if (downloadElement) {
                            downloadElement.style.display = 'block'; // Make the download link visible
                        }
                        statusElement.innerText = data.status; // Set text to "Completed"
                    } else {
                        // Update progress bar width based on the task progress
                        let progress = 0;
                        if (data.status === 'PROGRESS' && data.result) {
                            progress = data.result.progress;
                        }
                        if (progressBarElement) {
                            progressBarElement.style.width = progress + '%';
                        }
                        statusElement.innerText = data.status; // Set text to the current status
                    }
                })
                .catch(error => console.error('Error:', error));
        };

        setInterval(updateProgress, 2000);
    });
});
