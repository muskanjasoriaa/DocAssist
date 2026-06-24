document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const uploadStatusText = document.getElementById('uploadStatusText');
    const documentList = document.getElementById('documentList');
    const activeDocTitle = document.getElementById('activeDocTitle');
    const activeDocSub = document.getElementById('activeDocSub');
    const messagesContainer = document.getElementById('messagesContainer');
    const welcomeBox = document.getElementById('welcomeBox');
    const chatForm = document.getElementById('chatForm');
    const queryInput = document.getElementById('queryInput');
    const sendBtn = document.getElementById('sendBtn');
    const apiStatusDot = document.getElementById('apiStatusDot');
    const apiStatusText = document.getElementById('apiStatusText');

    let activeDocumentId = null;
    let documents = [];

    // Initialize API Status Indicator
    function updateApiStatus(active, message) {
        if (active) {
            apiStatusDot.className = 'fa-solid fa-circle-nodes status-dot active';
            apiStatusText.innerText = message || 'Local RAG Server Active';
        } else {
            apiStatusDot.className = 'fa-solid fa-circle-nodes status-dot';
            apiStatusDot.style.color = '#EF4444';
            apiStatusDot.style.textShadow = '0 0 8px rgba(239, 68, 68, 0.4)';
            apiStatusText.innerText = message || 'Server Offline';
        }
    }

    // Format Date Helper
    function formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString(undefined, { 
                month: 'short', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } catch (e) {
            return dateString;
        }
    }

    // Markdown Parser Helper
    function formatMessageText(text) {
        // Escape HTML
        let clean = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Format code blocks ```code```
        clean = clean.replace(/```([\s\S]+?)```/g, '<pre><code>$1</code></pre>');

        // Format inline code `code`
        clean = clean.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Format bold text **bold**
        clean = clean.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Convert double newlines to paragraph tags, single to line breaks
        return clean.split(/\n\n+/).map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    }

    // Render Library list
    function renderLibrary() {
        if (documents.length === 0) {
            documentList.innerHTML = `
                <div class="no-docs-message">
                    <i class="fa-regular fa-file-pdf"></i>
                    <p>No documents uploaded yet.</p>
                </div>
            `;
            return;
        }

        documentList.innerHTML = documents.map(doc => {
            let statusIcon = '<i class="fa-regular fa-file-pdf ready"></i>';
            if (doc.status === 'processing') {
                statusIcon = '<i class="fa-solid fa-spinner fa-spin processing"></i>';
            } else if (doc.status === 'failed') {
                statusIcon = '<i class="fa-solid fa-triangle-exclamation failed"></i>';
            }

            const activeClass = doc.id === activeDocumentId ? 'active' : '';

            return `
                <div class="doc-item ${activeClass}" data-id="${doc.id}">
                    <div class="doc-info">
                        ${statusIcon}
                        <div class="doc-details">
                            <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
                            <span class="doc-meta">${formatDate(doc.upload_time)}</span>
                        </div>
                    </div>
                    <button class="btn-delete" data-id="${doc.id}" title="Delete document">
                        <i class="fa-regular fa-trash-can"></i>
                    </button>
                </div>
            `;
        }).join('');

        // Attach event listeners
        documentList.querySelectorAll('.doc-item').forEach(item => {
            item.addEventListener('click', (e) => {
                // Ignore click if clicking the delete button
                if (e.target.closest('.btn-delete')) return;
                const docId = parseInt(item.getAttribute('data-id'));
                selectDocument(docId);
            });
        });

        documentList.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const docId = parseInt(btn.getAttribute('data-id'));
                deleteDocument(docId);
            });
        });
    }

    // Fetch library documents
    async function loadLibrary() {
        try {
            const res = await fetch('/api/documents');
            if (!res.ok) throw new Error('Failed to load documents');
            documents = await res.json();
            renderLibrary();
            updateApiStatus(true);
        } catch (error) {
            console.error('Error fetching documents:', error);
            updateApiStatus(false, 'Connection Failed');
        }
    }

    // Select active document
    function selectDocument(docId) {
        const doc = documents.find(d => d.id === docId);
        if (!doc) return;

        if (doc.status !== 'ready') {
            alert(`Document is ${doc.status}. Please wait until it is processed successfully.`);
            return;
        }

        activeDocumentId = docId;
        
        // Update headers
        activeDocTitle.innerText = doc.filename;
        activeDocSub.innerText = `ID: ${doc.id} | Status: Ready for queries`;
        
        // Enable input fields
        queryInput.disabled = false;
        sendBtn.disabled = false;
        queryInput.placeholder = `Ask a question about "${doc.filename}"...`;

        // Clear messages container and show welcome
        messagesContainer.innerHTML = '';
        if (welcomeBox) welcomeBox.style.display = 'none';

        // Re-render library list to show active highlight
        renderLibrary();

        // Focus chat input
        queryInput.focus();
    }

    // Upload Document
    async function uploadFile(file) {
        if (!file || !file.name.endsWith('.pdf')) {
            alert('Please select a valid PDF file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        // Reset and display progress bar
        uploadProgress.style.display = 'block';
        progressFill.style.width = '20%';
        uploadStatusText.innerText = 'Uploading...';

        try {
            const response = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Upload failed');
            }

            progressFill.style.width = '100%';
            uploadStatusText.innerText = 'Processing document...';

            // Refresh library lists
            await loadLibrary();

            // Set timeout to hide progress
            setTimeout(() => {
                uploadProgress.style.display = 'none';
                progressFill.style.width = '0%';
            }, 3000);

        } catch (error) {
            console.error('Upload Error:', error);
            alert(`Upload failed: ${error.message}`);
            uploadProgress.style.display = 'none';
        }
    }

    // Delete Document
    async function deleteDocument(docId) {
        if (!confirm('Are you sure you want to delete this document and all its data?')) return;

        try {
            const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Delete request failed');
            
            // If the deleted document was active, reset active view
            if (activeDocumentId === docId) {
                activeDocumentId = null;
                activeDocTitle.innerText = 'Select a document to begin chat';
                activeDocSub.innerText = 'Upload a PDF in the sidebar and click on it to start asking questions.';
                queryInput.disabled = true;
                sendBtn.disabled = true;
                queryInput.placeholder = 'Ask a question about this document...';
                messagesContainer.innerHTML = '';
                if (welcomeBox) welcomeBox.style.display = 'flex';
            }

            await loadLibrary();
        } catch (error) {
            console.error('Error deleting document:', error);
            alert('Failed to delete document.');
        }
    }

    // Append Message to Chat Bubble
    function appendMessage(sender, text) {
        if (welcomeBox) welcomeBox.style.display = 'none';

        const messageEl = document.createElement('div');
        messageEl.className = `message message-${sender}`;

        const isUser = sender === 'user';
        const avatarIcon = isUser ? 'fa-user' : 'fa-robot';
        
        messageEl.innerHTML = `
            <div class="avatar">
                <i class="fa-solid ${avatarIcon}"></i>
            </div>
            <div class="message-content">
                ${isUser ? `<p>${text}</p>` : formatMessageText(text)}
            </div>
        `;

        messagesContainer.appendChild(messageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Append typing indicator
    function appendTypingIndicator() {
        const indicatorEl = document.createElement('div');
        indicatorEl.className = 'message message-ai typing-indicator-el';
        indicatorEl.innerHTML = `
            <div class="avatar">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        messagesContainer.appendChild(indicatorEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Remove typing indicator
    function removeTypingIndicator() {
        const indicator = messagesContainer.querySelector('.typing-indicator-el');
        if (indicator) indicator.remove();
    }

    // Handle Chat Submission
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query || !activeDocumentId) return;

        // Reset input
        queryInput.value = '';
        
        // Append user message
        appendMessage('user', query);

        // Show typing animation
        appendTypingIndicator();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_id: activeDocumentId,
                    message: query
                })
            });

            removeTypingIndicator();

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Chat query failed');
            }

            const data = await res.json();
            appendMessage('ai', data.answer);

        } catch (error) {
            removeTypingIndicator();
            console.error('Chat Error:', error);
            appendMessage('ai', `❌ **Error querying document:** ${error.message}`);
        }
    });

    // File selection listeners
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    // Drag and Drop listeners
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    // Initial load
    loadLibrary();

    // Poll library every 5 seconds to update processing status of files
    setInterval(() => {
        const hasProcessingDocs = documents.some(d => d.status === 'processing');
        if (hasProcessingDocs) {
            loadLibrary();
        }
    }, 5000);
});
