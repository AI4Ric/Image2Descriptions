document.addEventListener('DOMContentLoaded', function () {
    const uploads = document.querySelectorAll('[data-task-id]');

    uploads.forEach(upload => {
        const taskId = upload.dataset.taskId;
        const statusElement = document.getElementById(`status-${taskId}`);
        const progressBarElement = document.getElementById(`progress-bar-${taskId}`);
        const downloadElement = document.getElementById(`download-${taskId}`); 
        const imagesDownloadLink = document.querySelector(`.download-images-link[data-task-id="${taskId}"]`);

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
                        if (imagesDownloadLink) {
                            imagesDownloadLink.style.display = 'block';
                        }
                        statusElement.innerText = data.status; // Set text to "Completed"
                    } else {
                        // Update progress bar width based on the task progress
                        let progress = 0;
                        if (data.status === 'PROGRESS' && data.result) {
                            progress = data.result.percent;
                        }
                        if (progressBarElement) {
                            console.log(`Progress bar element found for task ${taskId}`);
                            progressBarElement.style.width = progress + '%';
                            console.log(`Progress bar width set to ${progressBarElement.style.width}`);
                        }
                        statusElement.innerText = data.status; // Set text to the current status
                    }
                })
                .catch(error => console.error('Error:', error));
        };

        setInterval(updateProgress, 2000);
    });
});
