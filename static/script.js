document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const fileInput = document.getElementById('file-input');
    const fileNamesSpan = document.getElementById('file-names');
    const uploadStatus = document.getElementById('upload-status');
    const uploadBtn = uploadForm.querySelector('button');
    const btnText = uploadBtn.querySelector('.btn-text');
    const spinner = uploadBtn.querySelector('.spinner');

    fileInput.addEventListener('change', () => {
        fileNamesSpan.textContent = fileInput.files.length > 0
            ? Array.from(fileInput.files).map(f => f.name).join(', ')
            : 'No files selected';
    });

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        if (fileInput.files.length === 0) {
            updateUploadStatus('Please select files to upload.', 'error');
            return;
        }
        const formData = new FormData(uploadForm);
        toggleSpinner(true);
        updateUploadStatus('Ingesting documents...', 'loading');
        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const result = await response.json();
            updateUploadStatus(response.ok ? result.message : result.error, response.ok ? 'success' : 'error');
        } catch (error) {
            updateUploadStatus('An error occurred.', 'error');
        } finally {
            toggleSpinner(false);
        }
    });

    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const userMessage = userInput.value.trim();
        if (!userMessage) return;
        addMessageToChat('user', userMessage);
        userInput.value = '';
        const loadingIndicator = addMessageToChat('bot', '...', null, true);
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage })
            });
            const data = await response.json();
            chatBox.removeChild(loadingIndicator);
            addMessageToChat('bot', response.ok ? data.answer : data.error, data.sources);
        } catch (error) {
            chatBox.removeChild(loadingIndicator);
            addMessageToChat('bot', "Error communicating with the server.");
        }
    });

    function toggleSpinner(show) {
        btnText.style.display = show ? 'none' : 'inline';
        spinner.style.display = show ? 'block' : 'none';
        uploadBtn.disabled = show;
    }

    function updateUploadStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.style.color = type === 'success' ? '#28a745' : (type === 'error' ? '#dc3545' : '#6c757d');
    }

    function addMessageToChat(sender, text, sources = null, isLoading = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (isLoading) {
            contentDiv.innerHTML = `<p><i class="fas fa-spinner fa-spin"></i></p>`;
        } else {
            const p = document.createElement('p');
            p.textContent = text;
            contentDiv.appendChild(p);
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.innerHTML = `<strong>Sources:</strong>`;
                const sourcesList = document.createElement('div');
                sourcesList.className = 'sources-list';
                sources.forEach(source => {
                    const sourceTag = document.createElement('span');
                    sourceTag.className = 'source-tag';
                    sourceTag.textContent = source;
                    sourcesList.appendChild(sourceTag);
});
                sourcesDiv.appendChild(sourcesList);
                contentDiv.appendChild(sourcesDiv);
            }
        }
        messageDiv.appendChild(contentDiv);
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        return messageDiv;
    }
});