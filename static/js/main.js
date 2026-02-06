let currentAudioUrl = null;
let currentFilename = null;
let wavesurfer = null;
let mediaRecorder = null;
let audioChunks = [];
let isPlaying = false;

// Initialize Wavesurfer
document.addEventListener('DOMContentLoaded', () => {
    wavesurfer = WaveSurfer.create({
        container: '#waveform',
        waveColor: '#1b3d6f',      // Genesys Navy
        progressColor: '#ff4f1f',   // Genesys Orange
        cursorColor: '#ff4f1f',
        barWidth: 3,
        barRadius: 3,
        cursorWidth: 2,
        height: 80,
        barGap: 2,
        responsive: true,
        normalize: true
    });

    // Update play button icon on play/pause
    wavesurfer.on('play', () => {
        isPlaying = true;
        updatePlayButton();
    });

    wavesurfer.on('pause', () => {
        isPlaying = false;
        updatePlayButton();
    });

    wavesurfer.on('finish', () => {
        isPlaying = false;
        updatePlayButton();
    });

    // Drop zone setup
    const dropZone = document.getElementById('dropZone');
    dropZone.addEventListener('click', () => document.getElementById('fileInput').click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    // Check for getUserMedia support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        document.getElementById('recordStatus').innerText = "Audio recording not supported in this browser.";
    }

    /* --- Event Listeners (Refactored from inline HTML) --- */

    // Tabs
    document.querySelectorAll('.gux-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabId = e.currentTarget.dataset.tab;
            if (tabId) switchTab(tabId);
        });
    });

    // Generate Button
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateTTS);
    }

    // Record Button
    const recordBtn = document.getElementById('recordBtn');
    if (recordBtn) {
        recordBtn.addEventListener('click', toggleRecording);
    }

    // Play Button
    // Note: The play button might be dynamic or hidden, but it exists in DOM.
    // However, if we re-create it or it's static, listener is fine.
    // Index.html has it static. 
    const playBtn = document.getElementById('playBtn');
    if (playBtn) {
        playBtn.addEventListener('click', playPause);
    }

    // Export Button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToGenesys);
    }

    // File Input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => handleFileSelect(e.target));
    }
});

function updatePlayButton() {
    const playBtn = document.querySelector('.gux-play-btn ion-icon');
    if (playBtn) {
        playBtn.setAttribute('name', isPlaying ? 'pause' : 'play');
        playBtn.style.marginLeft = isPlaying ? '0' : '3px';
    }
}

/* --- UI Logic --- */
function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.gux-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabId) {
            btn.classList.add('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.gux-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');

    // Trigger library loading when library tab is activated
    if (tabId === 'library') {
        onLibraryTabActivated();
    }
}

function showResult(url, filename) {
    currentAudioUrl = url;
    currentFilename = filename;

    const resultSection = document.getElementById('resultSection');
    resultSection.classList.add('visible');
    resultSection.style.display = 'block';

    wavesurfer.load(url);

    // Auto-fill prompt name (sanitized)
    const promptNameInput = document.getElementById('promptName');
    if (!promptNameInput.value) {
        let baseName = filename.split('.')[0];
        // Remove common prefixes
        baseName = baseName.replace(/^(tts_|upload_|recording_)/i, '');
        // Limit length
        baseName = baseName.substring(0, 30);
        promptNameInput.value = baseName || 'Prompt';
    }

    // Scroll to result section
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function playPause() {
    wavesurfer.playPause();
}

function setButtonLoading(buttonId, loading) {
    const btn = document.getElementById(buttonId);
    if (loading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

function showStatus(elementId, message, type) {
    const statusEl = document.getElementById(elementId);
    statusEl.textContent = message;
    statusEl.className = `gux-status visible gux-status-${type}`;
}

function hideStatus(elementId) {
    const statusEl = document.getElementById(elementId);
    statusEl.className = 'gux-status';
}

/* --- API Calls --- */

async function generateTTS() {
    const text = document.getElementById('ttsText').value.trim();
    const voice = document.getElementById('voiceSelect').value;

    if (!text) {
        alert("Please enter text to convert to speech.");
        return;
    }

    setButtonLoading('generateBtn', true);

    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice })
        });
        const data = await res.json();

        if (data.success) {
            showResult(data.url, data.filename);
        } else {
            alert("Error: " + data.error);
        }
    } catch (e) {
        console.error(e);
        alert("Network error. Please try again.");
    } finally {
        setButtonLoading('generateBtn', false);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showResult(data.url, data.filename);
        } else {
            alert("Upload failed: " + data.error);
        }
    } catch (e) {
        alert("Error uploading file. Please try again.");
    }
}

function handleFileSelect(input) {
    if (input.files.length) {
        uploadFile(input.files[0]);
    }
}

/* --- Recording Logic --- */
async function toggleRecording() {
    const btn = document.getElementById('recordBtn');
    const status = document.getElementById('recordStatus');

    if (mediaRecorder && mediaRecorder.state === 'recording') {
        // Stop recording
        mediaRecorder.stop();
        btn.classList.remove('recording');
        status.innerText = "Processing...";
    } else {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const file = new File([audioBlob], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
                await uploadFile(file);
                status.innerText = "Click to start recording";

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            btn.classList.add('recording');
            status.innerText = "Recording... Click to stop";

        } catch (e) {
            alert("Could not access microphone: " + e.message);
        }
    }
}

/* --- Export Logic --- */
async function exportToGenesys() {
    if (!currentFilename) {
        alert("No audio file to export. Please generate or upload a file first.");
        return;
    }

    const name = document.getElementById('promptName').value.trim();
    const desc = document.getElementById('promptDesc').value.trim();
    const language = document.getElementById('promptLanguage').value;

    if (!name) {
        alert("Please provide a prompt name.");
        return;
    }

    setButtonLoading('exportBtn', true);
    showStatus('exportStatus', 'Exporting to Genesys Cloud...', 'loading');

    try {
        const res = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: currentFilename,
                promptName: name,
                description: desc,
                language: language
            })
        });
        const data = await res.json();

        if (data.success) {
            showStatus('exportStatus', '✓ Successfully exported to Genesys Cloud!', 'success');
        } else {
            showStatus('exportStatus', 'Export Failed: ' + data.error, 'error');
        }
    } catch (e) {
        showStatus('exportStatus', 'Network Error. Please try again.', 'error');
    } finally {
        setButtonLoading('exportBtn', false);
    }
}

/* ===== PROMPT LIBRARY ===== */

// Library state
let libraryWavesurfer = null;
let libraryCurrentPrompt = null;
let libraryCurrentResources = [];
let libraryPage = 1;
let libraryPageSize = 15;
let librarySearch = '';
let librarySortBy = 'name';
let librarySortOrder = 'asc';
let libraryPagination = null;
let libraryIsPlaying = false;
let libraryLoaded = false;
let searchDebounceTimer = null;

// Initialize library wavesurfer
function initLibraryWavesurfer() {
    if (libraryWavesurfer) return;

    libraryWavesurfer = WaveSurfer.create({
        container: '#libraryWaveform',
        waveColor: '#1b3d6f',
        progressColor: '#ff4f1f',
        cursorColor: '#ff4f1f',
        barWidth: 3,
        barRadius: 3,
        cursorWidth: 2,
        height: 80,
        barGap: 2,
        responsive: true,
        normalize: true
    });

    libraryWavesurfer.on('play', () => {
        libraryIsPlaying = true;
        updateLibraryPlayButton();
    });

    libraryWavesurfer.on('pause', () => {
        libraryIsPlaying = false;
        updateLibraryPlayButton();
    });

    libraryWavesurfer.on('finish', () => {
        libraryIsPlaying = false;
        updateLibraryPlayButton();
    });
}

function updateLibraryPlayButton() {
    const playBtn = document.querySelector('#libraryPlayBtn ion-icon');
    if (playBtn) {
        playBtn.setAttribute('name', libraryIsPlaying ? 'pause' : 'play');
        playBtn.style.marginLeft = libraryIsPlaying ? '0' : '3px';
    }
}

// Load prompts from API
async function loadPrompts() {
    const loadingEl = document.getElementById('promptsLoading');
    const tableEl = document.getElementById('promptsTable');
    const emptyEl = document.getElementById('promptsEmpty');
    const paginationEl = document.getElementById('promptsPagination');

    // Show loading
    loadingEl.style.display = 'flex';
    tableEl.style.display = 'none';
    emptyEl.style.display = 'none';
    paginationEl.style.display = 'none';

    try {
        const params = new URLSearchParams({
            page: libraryPage,
            pageSize: libraryPageSize,
            sortBy: librarySortBy,
            sortOrder: librarySortOrder
        });

        if (librarySearch) {
            params.append('search', librarySearch);
        }

        const res = await fetch(`/api/prompts?${params}`);
        const data = await res.json();

        loadingEl.style.display = 'none';

        if (!data.success) {
            throw new Error(data.error || 'Failed to load prompts');
        }

        libraryPagination = data.pagination;

        if (data.prompts.length === 0) {
            emptyEl.style.display = 'flex';
            return;
        }

        // Render prompts table
        renderPromptsTable(data.prompts);
        tableEl.style.display = 'table';

        // Update pagination
        updatePagination();
        paginationEl.style.display = 'flex';

    } catch (e) {
        console.error('Error loading prompts:', e);
        loadingEl.style.display = 'none';
        emptyEl.querySelector('p').textContent = 'Error loading prompts: ' + e.message;
        emptyEl.style.display = 'flex';
    }
}

// Render prompts table
function renderPromptsTable(prompts) {
    const tbody = document.getElementById('promptsTableBody');
    tbody.innerHTML = '';

    prompts.forEach(prompt => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td data-label="Name">
                <span class="prompt-name">${escapeHtml(prompt.name)}</span>
            </td>
            <td data-label="Description">
                <span class="prompt-description" title="${escapeHtml(prompt.description)}">
                    ${escapeHtml(prompt.description) || '—'}
                </span>
            </td>
            <td data-label="Languages">
                <div class="prompt-languages" id="langs-${prompt.id}">
                    <span class="gux-language-badge">Loading...</span>
                </div>
            </td>
            <td data-label="Actions">
                <div class="prompt-actions">
                    <button class="gux-btn-icon play-prompt-btn" data-prompt-id="${prompt.id}" data-prompt-name="${escapeHtml(prompt.name)}" title="Play">
                        <ion-icon name="play-outline"></ion-icon>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);

        // Load resources for this prompt (async)
        loadPromptLanguages(prompt.id);
    });

    // Attach click handlers to play buttons
    document.querySelectorAll('.play-prompt-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const promptId = this.dataset.promptId;
            const promptName = this.dataset.promptName;
            playPrompt(promptId, promptName);
        });
    });
}

// Load language resources for a prompt
async function loadPromptLanguages(promptId) {
    const container = document.getElementById(`langs-${promptId}`);
    if (!container) return;

    try {
        const res = await fetch(`/api/prompts/${promptId}/resources`);
        const data = await res.json();

        if (!data.success || !data.resources || data.resources.length === 0) {
            container.innerHTML = '<span class="gux-language-badge">No audio</span>';
            return;
        }

        container.innerHTML = data.resources.map(r => `
            <span class="gux-language-badge ${r.has_audio ? 'has-audio' : ''}" 
                  title="${r.has_audio ? 'Audio available' : 'No audio'}">
                ${r.language.toUpperCase()}
            </span>
        `).join('');

    } catch (e) {
        container.innerHTML = '<span class="gux-language-badge">Error</span>';
    }
}

// Play a prompt
async function playPrompt(promptId, promptName) {
    initLibraryWavesurfer();

    const playerSection = document.getElementById('libraryPlayerSection');
    const titleEl = document.getElementById('libraryPlayerTitle');
    const languageSelect = document.getElementById('libraryLanguageSelect');

    // Show player section
    playerSection.style.display = 'block';
    titleEl.textContent = `Now Playing: ${promptName}`;

    libraryCurrentPrompt = { id: promptId, name: promptName };

    try {
        // Fetch resources
        const res = await fetch(`/api/prompts/${promptId}/resources`);
        const data = await res.json();

        if (!data.success || !data.resources || data.resources.length === 0) {
            alert('No audio resources found for this prompt.');
            return;
        }

        libraryCurrentResources = data.resources.filter(r => r.has_audio);

        if (libraryCurrentResources.length === 0) {
            alert('No audio files available for this prompt.');
            return;
        }

        // Populate language selector
        languageSelect.innerHTML = libraryCurrentResources.map(r =>
            `<option value="${r.language}">${r.language.toUpperCase()}</option>`
        ).join('');

        // Load first language
        await loadLibraryAudio(promptId, libraryCurrentResources[0].language);

        // Scroll to player
        playerSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (e) {
        console.error('Error loading prompt:', e);
        alert('Error loading prompt: ' + e.message);
    }
}

// Load audio for library player
async function loadLibraryAudio(promptId, language) {
    try {
        const res = await fetch(`/api/prompts/${promptId}/audio/${language}`);
        const data = await res.json();

        if (!data.success || !data.audio_url) {
            throw new Error('Audio URL not available');
        }

        // Load into wavesurfer
        libraryWavesurfer.load(data.audio_url);

    } catch (e) {
        console.error('Error loading audio:', e);
        alert('Error loading audio: ' + e.message);
    }
}

// Handle library language change
function onLibraryLanguageChange() {
    if (!libraryCurrentPrompt) return;

    const language = document.getElementById('libraryLanguageSelect').value;
    loadLibraryAudio(libraryCurrentPrompt.id, language);
}

// Library play/pause
function libraryPlayPause() {
    if (libraryWavesurfer) {
        libraryWavesurfer.playPause();
    }
}

// Update pagination UI
function updatePagination() {
    if (!libraryPagination) return;

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const infoEl = document.getElementById('paginationInfo');

    prevBtn.disabled = libraryPage <= 1;
    nextBtn.disabled = libraryPage >= libraryPagination.page_count;

    infoEl.textContent = `Page ${libraryPagination.page_number} of ${libraryPagination.page_count} (${libraryPagination.total} prompts)`;
}

// Pagination handlers
function previousPage() {
    if (libraryPage > 1) {
        libraryPage--;
        loadPrompts();
    }
}

function nextPage() {
    if (libraryPagination && libraryPage < libraryPagination.page_count) {
        libraryPage++;
        loadPrompts();
    }
}

// Search handler with debounce
function onLibrarySearch(e) {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        librarySearch = e.target.value.trim();
        libraryPage = 1; // Reset to first page
        loadPrompts();
    }, 300);
}

// Refresh library
function refreshLibrary() {
    libraryPage = 1;
    loadPrompts();
}

// Escape HTML helper
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize library when tab is shown
function onLibraryTabActivated() {
    if (!libraryLoaded) {
        libraryLoaded = true;
        loadPrompts();
    }
}

// ===== TRANSCRIPTION FUNCTIONALITY =====

let isTranscribing = false;

// Transcribe current prompt
async function transcribeCurrentPrompt() {
    if (!libraryCurrentPrompt) {
        alert('No prompt selected. Please play a prompt first.');
        return;
    }
    
    if (isTranscribing) {
        return; // Already transcribing
    }
    
    const language = document.getElementById('libraryLanguageSelect').value;
    const transcribeBtn = document.getElementById('transcribeBtn');
    const transcriptionSection = document.getElementById('transcriptionSection');
    const transcriptionLoading = document.getElementById('transcriptionLoading');
    const transcriptionContent = document.getElementById('transcriptionContent');
    const originalTextEl = document.getElementById('originalText');
    const translatedTextEl = document.getElementById('translatedText');
    const detectedLangEl = document.getElementById('detectedLanguage');
    
    // Show loading state
    isTranscribing = true;
    transcribeBtn.classList.add('loading');
    transcribeBtn.disabled = true;
    transcriptionSection.style.display = 'block';
    transcriptionLoading.style.display = 'flex';
    transcriptionContent.style.display = 'none';
    
    try {
        const res = await fetch(`/api/prompts/${libraryCurrentPrompt.id}/transcribe/${language}`);
        const data = await res.json();
        
        if (data.success) {
            // Show transcription results
            originalTextEl.textContent = data.original_text || '(No speech detected)';
            translatedTextEl.textContent = data.translated_text || '(No translation available)';
            detectedLangEl.textContent = data.detected_language || language;
            
            transcriptionLoading.style.display = 'none';
            transcriptionContent.style.display = 'block';
        } else {
            throw new Error(data.error || 'Transcription failed');
        }
    } catch (e) {
        console.error('Transcription error:', e);
        transcriptionLoading.style.display = 'none';
        transcriptionContent.style.display = 'block';
        originalTextEl.textContent = 'Error: ' + e.message;
        translatedTextEl.textContent = '';
        detectedLangEl.textContent = '-';
    } finally {
        isTranscribing = false;
        transcribeBtn.classList.remove('loading');
        transcribeBtn.disabled = false;
    }
}

// Clear transcription when language changes
function clearTranscription() {
    const transcriptionSection = document.getElementById('transcriptionSection');
    if (transcriptionSection) {
        transcriptionSection.style.display = 'none';
    }
}

// Setup library event listeners
function setupLibraryEventListeners() {
    // Search input
    const searchInput = document.getElementById('librarySearch');
    if (searchInput) {
        searchInput.addEventListener('input', onLibrarySearch);
    }

    // Refresh button
    const refreshBtn = document.getElementById('refreshLibraryBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshLibrary);
    }

    // Pagination buttons
    const prevBtn = document.getElementById('prevPageBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', previousPage);
    }

    const nextBtn = document.getElementById('nextPageBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', nextPage);
    }

    // Library play button
    const libraryPlayBtn = document.getElementById('libraryPlayBtn');
    if (libraryPlayBtn) {
        libraryPlayBtn.addEventListener('click', libraryPlayPause);
    }

    // Language selector
    const languageSelect = document.getElementById('libraryLanguageSelect');
    if (languageSelect) {
        languageSelect.addEventListener('change', function() {
            onLibraryLanguageChange();
            clearTranscription();
        });
    }

    // Transcribe button
    const transcribeBtn = document.getElementById('transcribeBtn');
    if (transcribeBtn) {
        transcribeBtn.addEventListener('click', transcribeCurrentPrompt);
    }
}

// Call setup on DOM ready
document.addEventListener('DOMContentLoaded', setupLibraryEventListeners);
