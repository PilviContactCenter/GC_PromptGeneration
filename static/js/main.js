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
    });
    event.currentTarget.classList.add('active');

    // Update tab content
    document.querySelectorAll('.gux-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');
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
