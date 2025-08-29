// Dark mode toggle
document.getElementById('darkModeToggle').addEventListener('click', function() {
    document.documentElement.classList.toggle('dark');
});

// Mode switching
const recordModeBtn = document.getElementById('recordModeBtn');
const streamModeBtn = document.getElementById('streamModeBtn');
const recordingUI = document.getElementById('recordingUI');
const streamUI = document.getElementById('streamUI');

recordModeBtn.addEventListener('click', function() {
    recordModeBtn.classList.add('bg-white', 'dark:bg-gray-800', 'shadow-sm', 'text-primary-600', 'dark:text-primary-400');
    recordModeBtn.classList.remove('text-gray-600', 'dark:text-gray-300');
    streamModeBtn.classList.add('text-gray-600', 'dark:text-gray-300');
    streamModeBtn.classList.remove('bg-white', 'dark:bg-gray-800', 'shadow-sm', 'text-primary-600', 'dark:text-primary-400');
    
    recordingUI.classList.remove('hidden');
    streamUI.classList.add('hidden');
    
    // Reset states when switching
    document.getElementById('readyState').classList.remove('hidden');
    document.getElementById('recordingState').classList.add('hidden');
    document.getElementById('playbackState').classList.add('hidden');
    document.getElementById('streamControls').classList.add('hidden');
});

streamModeBtn.addEventListener('click', function() {
    streamModeBtn.classList.add('bg-white', 'dark:bg-gray-800', 'shadow-sm', 'text-primary-600', 'dark:text-primary-400');
    streamModeBtn.classList.remove('text-gray-600', 'dark:text-gray-300');
    recordModeBtn.classList.add('text-gray-600', 'dark:text-gray-300');
    recordModeBtn.classList.remove('bg-white', 'dark:bg-gray-800', 'shadow-sm', 'text-primary-600', 'dark:text-primary-400');
    
    recordingUI.classList.add('hidden');
    streamUI.classList.remove('hidden');
});

// Recording functionality
let mediaRecorder;
let audioChunks = [];
let currentAudioBlob = null;
let recordingStartTime = null;
let recordingTimer = null;

// Recording mode interactions
const startRecordingBtn = document.getElementById('startRecordingBtn');
const stopRecordingBtn = document.getElementById('stopRecordingBtn');
const sendRecordingBtn = document.getElementById('sendRecordingBtn');
const readyState = document.getElementById('readyState');
const recordingState = document.getElementById('recordingState');
const playbackState = document.getElementById('playbackState');

// Initialize recording
async function initializeRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            currentAudioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            audioChunks = [];
        };
        
        return true;
    } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Unable to access microphone. Please check permissions.');
        return false;
    }
}

// Format time display
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Update recording timer
function updateRecordingTimer() {
    if (recordingStartTime) {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const timerElement = recordingState.querySelector('span');
        if (timerElement) {
            timerElement.textContent = `Recording... ${formatTime(elapsed)}`;
        }
    }
}

startRecordingBtn.addEventListener('click', async function() {
    const initialized = await initializeRecording();
    if (!initialized) return;
    
    readyState.classList.add('hidden');
    recordingState.classList.remove('hidden');
    
    // Start recording
    audioChunks = [];
    mediaRecorder.start();
    recordingStartTime = Date.now();
    recordingTimer = setInterval(updateRecordingTimer, 1000);
});

stopRecordingBtn.addEventListener('click', function() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        clearInterval(recordingTimer);
        recordingTimer = null;
        recordingStartTime = null;
    }
    
    recordingState.classList.add('hidden');
    playbackState.classList.remove('hidden');
    
    // Add functionality to the playback controls
    setTimeout(() => {
        const playbackPlayBtn = playbackState.querySelector('button .fa-play');
        const rerecordBtn = playbackState.querySelector('button .fa-redo');
        const deleteBtn = playbackState.querySelector('button .fa-trash');
        
        if (playbackPlayBtn) {
            const playBtn = playbackPlayBtn.parentElement;
            playBtn.addEventListener('click', function() {
                if (currentAudioBlob) {
                    const audioUrl = URL.createObjectURL(currentAudioBlob);
                    playAudio(audioUrl, playBtn);
                }
            });
        }
        
        if (rerecordBtn) {
            const rerecordButton = rerecordBtn.parentElement;
            rerecordButton.addEventListener('click', function() {
                playbackState.classList.add('hidden');
                readyState.classList.remove('hidden');
                currentAudioBlob = null;
            });
        }
        
        if (deleteBtn) {
            const deleteButton = deleteBtn.parentElement;
            deleteButton.addEventListener('click', function() {
                playbackState.classList.add('hidden');
                readyState.classList.remove('hidden');
                currentAudioBlob = null;
            });
        }
    }, 100);
});

sendRecordingBtn.addEventListener('click', async function() {
    if (!currentAudioBlob) return;
    
    playbackState.classList.add('hidden');
    readyState.classList.remove('hidden');
    
    // Create audio URL for playback
    const audioUrl = URL.createObjectURL(currentAudioBlob);
    const duration = Math.floor(currentAudioBlob.size / 16000); // Rough estimate
    
    // Add user message to chat
    const chatContainer = document.getElementById('chatContainer');
    const userMessage = document.createElement('div');
    userMessage.className = 'flex justify-end';
    userMessage.innerHTML = `
        <div class="max-w-xs md:max-w-md lg:max-w-lg bg-primary-500 dark:bg-primary-600 rounded-2xl p-4 shadow-sm text-white voice-bubble">
            <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-medium">You</span>
                <span class="text-xs opacity-80">Just now</span>
            </div>
            <div class="waveform text-white mb-2">
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-xs opacity-80">${formatTime(Math.max(1, Math.floor(duration / 1000)))}</span>
                <button class="opacity-80 hover:opacity-100 play-btn" data-audio-url="${audioUrl}">
                    <i class="fas fa-play"></i>
                </button>
            </div>
        </div>
    `;
    chatContainer.appendChild(userMessage);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Add click event to play button
    const playBtn = userMessage.querySelector('.play-btn');
    playBtn.addEventListener('click', function() {
        playAudio(audioUrl, playBtn);
    });
    
    // Show loading message
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'flex justify-start';
    loadingMessage.innerHTML = `
        <div class="max-w-xs md:max-w-md lg:max-w-lg bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm voice-bubble">
            <div class="flex items-center space-x-2 mb-1">
                <div class="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-primary-600 dark:text-primary-400">
                    <i class="fas fa-robot text-xs"></i>
                </div>
                <span class="text-xs font-medium text-gray-500 dark:text-gray-400">AI Assistant</span>
            </div>
            <div class="flex items-center space-x-2">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                <span class="text-sm text-gray-600 dark:text-gray-300">Processing...</span>
            </div>
        </div>
    `;
    chatContainer.appendChild(loadingMessage);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        // Send audio to API
        const response = await sendAudioToAPI(currentAudioBlob);
        
        // Remove loading message
        chatContainer.removeChild(loadingMessage);
        
        // Add bot response
        addBotResponse(response, chatContainer);
        
    } catch (error) {
        console.error('Error sending audio:', error);
        
        // Remove loading message
        chatContainer.removeChild(loadingMessage);
        
        // Show error message
        const errorMessage = document.createElement('div');
        errorMessage.className = 'flex justify-start';
        errorMessage.innerHTML = `
            <div class="max-w-xs md:max-w-md lg:max-w-lg bg-red-100 dark:bg-red-900 rounded-2xl p-4 shadow-sm">
                <div class="flex items-center space-x-2 mb-1">
                    <div class="w-6 h-6 rounded-full bg-red-200 dark:bg-red-800 flex items-center justify-center text-red-600 dark:text-red-400">
                        <i class="fas fa-exclamation-triangle text-xs"></i>
                    </div>
                    <span class="text-xs font-medium text-red-600 dark:text-red-400">Error</span>
                </div>
                <span class="text-sm text-red-700 dark:text-red-300">Failed to send audio. Please try again.</span>
            </div>
        `;
        chatContainer.appendChild(errorMessage);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Clear current recording
    currentAudioBlob = null;
});

// API functions
async function sendAudioToAPI(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('use_cache', 'false');
    
    const response = await fetch('http://localhost:8000/v1/voice/query', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response;
}

async function addBotResponse(response, chatContainer) {
    // First, let's check what we actually received
    console.log('Response headers:', response.headers);
    console.log('Content-Type:', response.headers.get('content-type'));
    
    const contentType = response.headers.get('content-type');
    
    try {
        // Parse as JSON first to see the structure
        const responseData = await response.json();
        console.log('Response data:', responseData);
        
        // Check if the response contains audio data or audio URL
        if (responseData.audio_url || responseData.audio || responseData.audio_data || responseData.audio_b64) {
            // Handle audio response from JSON
            let audioUrl;
            
            if (responseData.audio_url) {
                audioUrl = responseData.audio_url;
            } else if (responseData.audio_b64) {
                // Handle base64 audio from your API
                const audioBlob = base64ToBlob(responseData.audio_b64, 'audio/wav');
                audioUrl = URL.createObjectURL(audioBlob);
            } else if (responseData.audio_data) {
                // If audio is base64 encoded
                const audioBlob = base64ToBlob(responseData.audio_data, 'audio/wav');
                audioUrl = URL.createObjectURL(audioBlob);
            } else if (responseData.audio) {
                // Handle other audio formats
                const audioBlob = new Blob([responseData.audio], { type: 'audio/wav' });
                audioUrl = URL.createObjectURL(audioBlob);
            }
            
            const botMessage = document.createElement('div');
            botMessage.className = 'flex justify-start';
            botMessage.innerHTML = `
                <div class="max-w-xs md:max-w-md lg:max-w-lg bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm voice-bubble">
                    <div class="flex items-center space-x-2 mb-1">
                        <div class="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-primary-600 dark:text-primary-400">
                            <i class="fas fa-robot text-xs"></i>
                        </div>
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-400">AI Assistant</span>
                    </div>
                
                    <div class="waveform text-primary-600 dark:text-primary-400 mb-2">
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-xs text-gray-500 dark:text-gray-400">${responseData.llm_text ? responseData.llm_text.substring(0, 30) + '...' : 'Response'}</span>
                        <button class="text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300 play-btn" data-audio-url="${audioUrl}">
                            <i class="fas fa-play"></i>
                        </button>
                    </div>
                </div>
            `;
            chatContainer.appendChild(botMessage);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Add click event to play button
            const playBtn = botMessage.querySelector('.play-btn');
            playBtn.addEventListener('click', function() {
                playAudio(audioUrl, playBtn);
            });
            
            // Check for gold nudge and add it after a short delay
            if (responseData.gold_nudge) {
                setTimeout(() => {
                    addGoldNudgeMessage(responseData.gold_nudge, chatContainer);
                }, 1000);
            }
            
        } else {
            // Handle text/JSON response
            const botMessage = document.createElement('div');
            botMessage.className = 'flex justify-start';
            botMessage.innerHTML = `
                <div class="max-w-xs md:max-w-md lg:max-w-lg bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm">
                    <div class="flex items-center space-x-2 mb-1">
                        <div class="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-primary-600 dark:text-primary-400">
                            <i class="fas fa-robot text-xs"></i>
                        </div>
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-400">AI Assistant</span>
                    </div>
                    <div class="text-sm text-gray-700 dark:text-gray-300">${responseData.message || responseData.text || JSON.stringify(responseData)}</div>
                </div>
            `;
            chatContainer.appendChild(botMessage);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
    } catch (error) {
        console.error('Error parsing JSON response:', error);
        
        // Try to handle as direct audio blob
        try {
            const audioBlob = await response.blob();
            if (audioBlob.type.includes('audio')) {
                const audioUrl = URL.createObjectURL(audioBlob);
                const botMessage = document.createElement('div');
                botMessage.className = 'flex justify-start';
                botMessage.innerHTML = `
                    <div class="max-w-xs md:max-w-md lg:max-w-lg bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm voice-bubble">
                        <div class="flex items-center space-x-2 mb-1">
                            <div class="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-primary-600 dark:text-primary-400">
                                <i class="fas fa-robot text-xs"></i>
                            </div>
                            <span class="text-xs font-medium text-gray-500 dark:text-gray-400">AI Assistant</span>
                        </div>
                        <div class="waveform text-primary-600 dark:text-primary-400 mb-2">
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                            <div class="wave-bar"></div>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-gray-500 dark:text-gray-400">Response</span>
                            <button class="text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300 play-btn" data-audio-url="${audioUrl}">
                                <i class="fas fa-play"></i>
                            </button>
                        </div>
                    </div>
                `;
                chatContainer.appendChild(botMessage);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                // Add click event to play button
                const playBtn = botMessage.querySelector('.play-btn');
                playBtn.addEventListener('click', function() {
                    playAudio(audioUrl, playBtn);
                });
            } else {
                throw new Error('Not an audio blob');
            }
        } catch (blobError) {
            console.error('Error handling as blob:', blobError);
            // Show error message
            const botMessage = document.createElement('div');
            botMessage.className = 'flex justify-start';
            botMessage.innerHTML = `
                <div class="max-w-xs md:max-w-md lg:max-w-lg bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm">
                    <div class="flex items-center space-x-2 mb-1">
                        <div class="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-primary-600 dark:text-primary-400">
                            <i class="fas fa-robot text-xs"></i>
                        </div>
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-400">AI Assistant</span>
                    </div>
                    <div class="text-sm text-gray-700 dark:text-gray-300">Response received but format not recognized</div>
                </div>
            `;
            chatContainer.appendChild(botMessage);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
}

// Helper function to convert base64 to blob
function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

// Function to add gold nudge message
function addGoldNudgeMessage(goldNudge, chatContainer) {
    const nudgeMessage = document.createElement('div');
    nudgeMessage.className = 'flex justify-start';
    nudgeMessage.innerHTML = `
        <div class="max-w-xs md:max-w-md lg:max-w-lg bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900 dark:to-amber-900 rounded-2xl p-4 shadow-sm border border-yellow-200 dark:border-yellow-700">
            <div class="flex items-center space-x-2 mb-2">
                <div class="w-6 h-6 rounded-full bg-yellow-100 dark:bg-yellow-800 flex items-center justify-center text-yellow-600 dark:text-yellow-400">
                    <i class="fas fa-coins text-xs"></i>
                </div>
                <span class="text-xs font-medium text-yellow-700 dark:text-yellow-300">Investment Opportunity</span>
            </div>
            <div class="text-sm text-gray-700 dark:text-gray-300 mb-3">
                ${goldNudge.message}
            </div>
            <button class="w-full bg-gradient-to-r from-yellow-500 to-amber-500 hover:from-yellow-600 hover:to-amber-600 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 transform hover:scale-105 shadow-md gold-nudge-btn" data-link="${goldNudge.link}">
                <i class="fas fa-external-link-alt mr-2"></i>
                ${goldNudge.display_text}
            </button>
        </div>
    `;
    
    chatContainer.appendChild(nudgeMessage);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Add click event to the button
    const nudgeBtn = nudgeMessage.querySelector('.gold-nudge-btn');
    nudgeBtn.addEventListener('click', function() {
        const link = this.getAttribute('data-link');
        const fullUrl = `http://localhost:8000${link}`;
        window.open(fullUrl, '_blank');
    });
}

// Audio playback functionality
let currentlyPlayingAudio = null;
let currentPlayButton = null;

function playAudio(audioUrl, playButton) {
    // Stop any currently playing audio
    if (currentlyPlayingAudio) {
        currentlyPlayingAudio.pause();
        currentlyPlayingAudio.currentTime = 0;
        if (currentPlayButton) {
            currentPlayButton.innerHTML = '<i class="fas fa-play"></i>';
            currentPlayButton.parentElement.parentElement.classList.remove('playing');
        }
    }
    
    // If clicking the same button that was playing, just stop
    if (currentPlayButton === playButton && currentlyPlayingAudio) {
        currentlyPlayingAudio = null;
        currentPlayButton = null;
        return;
    }
    
    // Create and play new audio
    const audio = new Audio(audioUrl);
    currentlyPlayingAudio = audio;
    currentPlayButton = playButton;
    
    // Update button to show pause icon
    playButton.innerHTML = '<i class="fas fa-pause"></i>';
    playButton.parentElement.parentElement.classList.add('playing');
    
    audio.addEventListener('ended', function() {
        playButton.innerHTML = '<i class="fas fa-play"></i>';
        playButton.parentElement.parentElement.classList.remove('playing');
        currentlyPlayingAudio = null;
        currentPlayButton = null;
    });
    
    audio.addEventListener('error', function() {
        playButton.innerHTML = '<i class="fas fa-play"></i>';
        playButton.parentElement.parentElement.classList.remove('playing');
        currentlyPlayingAudio = null;
        currentPlayButton = null;
        alert('Error playing audio');
    });
    
    audio.play().catch(error => {
        console.error('Error playing audio:', error);
        playButton.innerHTML = '<i class="fas fa-play"></i>';
        playButton.parentElement.parentElement.classList.remove('playing');
        currentlyPlayingAudio = null;
        currentPlayButton = null;
    });
}

// Add click handlers to existing play buttons
document.addEventListener('DOMContentLoaded', function() {
    // Handle existing play buttons in the demo messages
    const existingPlayButtons = document.querySelectorAll('.voice-bubble button');
    existingPlayButtons.forEach(button => {
        if (button.querySelector('.fa-play')) {
            button.addEventListener('click', function() {
                // For demo purposes, create a simple beep sound
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
                gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
                
                // Visual feedback
                button.innerHTML = '<i class="fas fa-pause"></i>';
                button.parentElement.parentElement.classList.add('playing');
                
                setTimeout(() => {
                    button.innerHTML = '<i class="fas fa-play"></i>';
                    button.parentElement.parentElement.classList.remove('playing');
                }, 500);
            });
        }
    });
});

// WebSocket streaming functionality
let websocket = null;
let streamMediaRecorder = null;
let streamAudioChunks = [];
let isStreaming = false;
let currentStreamMessage = null;
let currentBotMessage = null;
let audioQueue = [];
let isPlayingResponse = false;
let audioContext = null;

// Stream mode interactions
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const streamControls = document.getElementById('streamControls');
const streamReadyText = document.getElementById('streamReadyText');

async function initializeWebSocket() {
    try {
        websocket = new WebSocket('ws://localhost:8000/v1/realtime/ws');
        
        websocket.onopen = function() {
            console.log('WebSocket connected');
            // Send handshake
            websocket.send(JSON.stringify({
                type: 'handshake',
                config: { lang: 'en' }
            }));
        };
        
        websocket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        };
        
        websocket.onclose = function() {
            console.log('WebSocket disconnected');
            websocket = null;
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
            alert('Failed to connect to streaming service');
        };
        
        return true;
    } catch (error) {
        console.error('Error initializing WebSocket:', error);
        return false;
    }
}

function handleWebSocketMessage(message) {
    console.log('WebSocket message:', message);
    
    switch (message.type) {
        case 'transcript.partial':
            updatePartialTranscript(message.text);
            break;
            
        case 'transcript.final':
            updateFinalTranscript(message.text, message.confidence);
            break;
            
        case 'output.audio_chunk':
            handleAudioChunk(message.audio);
            break;
    }
}

function updatePartialTranscript(text) {
    if (currentStreamMessage) {
        const transcriptElement = currentStreamMessage.querySelector('.transcript-text');
        if (transcriptElement) {
            transcriptElement.textContent = text;
            transcriptElement.classList.add('opacity-60');
        }
    }
}

function updateFinalTranscript(text, confidence) {
    if (currentStreamMessage) {
        const transcriptElement = currentStreamMessage.querySelector('.transcript-text');
        if (transcriptElement) {
            transcriptElement.textContent = text;
            transcriptElement.classList.remove('opacity-60');
        }
    }
    
    // Create bot response message
    createBotStreamMessage();
}

function createBotStreamMessage() {
    const chatContainer = document.getElementById('chatContainer');
    const botMessage = document.createElement('div');
    botMessage.className = 'flex justify-start';
    botMessage.innerHTML = `
        <div class="max-w-xs md:max-w-md lg:max-w-lg bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm voice-bubble">
            <div class="flex items-center space-x-2 mb-1">
                <div class="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-primary-600 dark:text-primary-400">
                    <i class="fas fa-robot text-xs"></i>
                </div>
                <span class="text-xs font-medium text-gray-500 dark:text-gray-400">AI Assistant</span>
                <div class="flex items-center space-x-1">
                    <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    <span class="text-xs opacity-80">Speaking</span>
                </div>
            </div>
            <div class="waveform text-primary-600 dark:text-primary-400 mb-2">
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
            </div>
        </div>
    `;
    chatContainer.appendChild(botMessage);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    currentBotMessage = botMessage;
}

async function handleAudioChunk(base64Audio) {
    try {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        const audioBlob = base64ToBlob(base64Audio, 'audio/wav');
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        audioQueue.push(audioBuffer);
        
        if (!isPlayingResponse) {
            playNextAudioChunk();
        }
    } catch (error) {
        console.error('Error handling audio chunk:', error);
    }
}

function playNextAudioChunk() {
    if (audioQueue.length === 0) {
        isPlayingResponse = false;
        if (currentBotMessage) {
            // Update bot message to show it's finished
            const statusElement = currentBotMessage.querySelector('.animate-pulse');
            if (statusElement) {
                statusElement.classList.remove('animate-pulse', 'bg-green-500');
                statusElement.classList.add('bg-gray-500');
                statusElement.nextElementSibling.textContent = 'Finished';
            }
        }
        return;
    }
    
    isPlayingResponse = true;
    const audioBuffer = audioQueue.shift();
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    
    source.onended = () => {
        playNextAudioChunk();
    };
    
    source.start();
}

async function startStreamRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamMediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
        });
        
        streamMediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && websocket && websocket.readyState === WebSocket.OPEN) {
                // Convert to base64 and send
                const reader = new FileReader();
                reader.onload = function() {
                    const base64 = reader.result.split(',')[1];
                    websocket.send(JSON.stringify({
                        type: 'input.audio',
                        audio: base64
                    }));
                };
                reader.readAsDataURL(event.data);
            }
        };
        
        // Send audio chunks every 100ms for real-time streaming
        streamMediaRecorder.start(100);
        return true;
    } catch (error) {
        console.error('Error starting stream recording:', error);
        return false;
    }
}

startStreamBtn.addEventListener('click', async function() {
    const wsConnected = await initializeWebSocket();
    if (!wsConnected) return;
    
    // Wait for WebSocket to be ready
    setTimeout(async () => {
        const recordingStarted = await startStreamRecording();
        if (!recordingStarted) return;
        
        isStreaming = true;
        streamControls.classList.remove('hidden');
        streamReadyText.classList.add('hidden');
        
        // Add streaming message to chat
        const chatContainer = document.getElementById('chatContainer');
        const streamMessage = document.createElement('div');
        streamMessage.className = 'flex justify-end';
        streamMessage.innerHTML = `
            <div class="max-w-xs md:max-w-md lg:max-w-lg bg-primary-500 dark:bg-primary-600 rounded-2xl p-4 shadow-sm text-white">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-medium">You (streaming)</span>
                    <div class="flex items-center space-x-1">
                        <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                        <span class="text-xs opacity-80">Live</span>
                    </div>
                </div>
                <div class="text-xs opacity-80 mb-2 transcript-text">Listening...</div>
                <div class="waveform text-white mb-2">
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                </div>
            </div>
        `;
        chatContainer.appendChild(streamMessage);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        currentStreamMessage = streamMessage;
    }, 500);
});

stopStreamBtn.addEventListener('click', function() {
    isStreaming = false;
    streamControls.classList.add('hidden');
    streamReadyText.classList.remove('hidden');
    
    // Stop recording
    if (streamMediaRecorder && streamMediaRecorder.state === 'recording') {
        streamMediaRecorder.stop();
        
        // Send commit message
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'input.commit'
            }));
        }
    }
    
    // Close WebSocket
    if (websocket) {
        websocket.close();
        websocket = null;
    }
    
    // Update streaming message
    if (currentStreamMessage) {
        const liveIndicator = currentStreamMessage.querySelector('.animate-pulse');
        if (liveIndicator) {
            liveIndicator.classList.remove('animate-pulse', 'bg-red-500');
            liveIndicator.classList.add('bg-gray-500');
            liveIndicator.nextElementSibling.textContent = 'Finished';
        }
        currentStreamMessage = null;
    }
    
    currentBotMessage = null;
});