// Mobile nav toggle
const navToggle = document.getElementById('navToggle');
const dashboardMenuBtn = document.getElementById("dashboardMenuBtn");
const dashboardMenu = document.getElementById("dashboardMenu");
const logoutMenuItem = document.getElementById("logoutMenuItem");

dashboardMenuBtn.addEventListener("click", (event) => {
    event.stopPropagation();
  
    const isOpen = dashboardMenu.classList.toggle("active");
    dashboardMenuBtn.setAttribute("aria-expanded", isOpen);
  });
  
  document.addEventListener("click", (event) => {
    if (
      !dashboardMenu.contains(event.target) &&
      !dashboardMenuBtn.contains(event.target)
    ) {
      dashboardMenu.classList.remove("active");
      dashboardMenuBtn.setAttribute("aria-expanded", "false");
    }
  });

  logoutMenuItem.addEventListener("click", async (event) => {
    event.preventDefault();
  
    const { error } = await supabaseClient.auth.signOut();
  
    if (error) {
      console.error("Logout failed:", error);
      alert("Logout failed. Please try again.");
      return;
    }
  
    window.location.href = "pages/login.html";
  });

const mainNav = document.getElementById('mainNav');
navToggle.addEventListener('click', () => {
	const open = mainNav.classList.toggle('open');
	navToggle.setAttribute('aria-expanded', open);
});
mainNav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
	mainNav.classList.remove('open');
	navToggle.setAttribute('aria-expanded', 'false');
}));

// Weather dropdown toggle
const weatherToggle = document.getElementById('weatherToggle');
const weatherCard = document.getElementById('weatherCard');
weatherToggle.addEventListener('click', () => {
	const isHidden = weatherCard.hasAttribute('hidden');
	if (isHidden) { weatherCard.removeAttribute('hidden'); weatherToggle.setAttribute('aria-expanded', 'true'); }
	else { weatherCard.setAttribute('hidden', ''); weatherToggle.setAttribute('aria-expanded', 'false'); }
});

// Voice orb interaction
const orbBtn = document.getElementById('orbBtn');
const voiceStage = document.querySelector('.voice-stage');
const orbLabel = document.getElementById('orbLabel');

const heroInner =
    document.querySelector('.hero-inner');

const voiceConversation =
    document.getElementById('voiceConversation');

const conversationMessages =
    document.getElementById('conversationMessages');

const conversationPlaceholder =
    document.getElementById('conversationPlaceholder');

const conversationStatus =
    document.getElementById('conversationStatus');

const conversationFooterText =
    document.getElementById('conversationFooterText');

let microphoneStream = null;
let microphoneRequestId = 0;

let ws = null;
let micAudioContext = null;
let micProcessor = null;
let micSource = null;

let playbackContext = null;
let nextPlayTime = 0;

// True while Gemini/Samarth is currently responding
let samarthIsSpeaking = false;

// Conversation transcript state
let userTranscript = "";
let assistantTranscript = "";

// Store the complete conversation
let conversationHistory = [];

function renderConversation() {
    if (!conversationMessages) return;

    conversationMessages.innerHTML = "";

    // Render completed conversation history
    conversationHistory.forEach(message => {
        const messageElement = document.createElement("div");

        messageElement.className =
            message.role === "user"
                ? "conversation-message user-message"
                : "conversation-message assistant-message";

        messageElement.innerHTML = `
            <div class="message-label">
                ${message.role === "user" ? "You" : "Samarth"}
            </div>
            <div class="message-text">
                ${escapeHtml(message.text)}
            </div>
        `;

        conversationMessages.appendChild(messageElement);
    });

    // Render current user message
    if (userTranscript.trim()) {
        const userMessage = document.createElement("div");

        userMessage.className =
            "conversation-message user-message";

        userMessage.innerHTML = `
            <div class="message-label">You</div>
            <div class="message-text">
                ${escapeHtml(userTranscript)}
            </div>
        `;

        conversationMessages.appendChild(userMessage);
    }

    // Render current Samarth response
    if (assistantTranscript.trim()) {
        const assistantMessage = document.createElement("div");

        assistantMessage.className =
            "conversation-message assistant-message";

        assistantMessage.innerHTML = `
            <div class="message-label">Samarth</div>
            <div class="message-text">
                ${escapeHtml(assistantTranscript)}
            </div>
        `;

        conversationMessages.appendChild(assistantMessage);
    }

    // Always keep the newest message visible
    conversationMessages.scrollTop =
        conversationMessages.scrollHeight;
}

const oldUser =
    document.getElementById(
        "live-user-message"
    );

if (oldUser) {
    oldUser.remove();
}

const oldAssistant =
    document.getElementById(
        "live-assistant-message"
    );

if (oldAssistant) {
    oldAssistant.remove();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


function updateLiveMessage(role, text) {

    if (!conversationMessages || !text.trim()) {
        return;
    }

    showConversation();

    const messageId =
        role === "user"
            ? "live-user-message"
            : "live-assistant-message";

    let message =
        document.getElementById(messageId);

    if (!message) {

        message =
            document.createElement("div");

        message.id = messageId;

        message.className =
            `conversation-message ${role}`;

        message.innerHTML = `
            <span class="message-label">
                ${role === "user" ? "YOU" : "SAMARTH"}
            </span>

            <div class="message-bubble"></div>
        `;

        conversationMessages.appendChild(message);
    }

    const bubble =
        message.querySelector(".message-bubble");

    bubble.textContent = text;

    conversationMessages.scrollTop =
        conversationMessages.scrollHeight;
}


function stopMicrophone() {

    // The Gemini Live API uses automatic voice activity detection (VAD)
// to detect the end of the user's speech.
// We keep the WebSocket session alive between turns.

if (ws && ws.readyState === WebSocket.OPEN) {

    ws.send(JSON.stringify({
        audio_end: true
    }));

    console.log(
        "Sent audio_end — Gemini Live session remains open."
    );
}

    // Stop microphone tracks
    if (microphoneStream) {
        microphoneStream.getTracks().forEach(track => track.stop());
        microphoneStream = null;
    }

    // Disconnect microphone audio processing
    if (micProcessor) {
        micProcessor.disconnect();
        micProcessor.onaudioprocess = null;
        micProcessor = null;
    }

    // Disconnect microphone source
    if (micSource) {
        micSource.disconnect();
        micSource = null;
    }

    // Close microphone audio context
    if (micAudioContext && micAudioContext.state !== "closed") {
        micAudioContext.close();
        micAudioContext = null;
    }

    orbBtn.classList.remove('listening');
    document.querySelector('.orb-title').textContent = 'Ask Samarth';
    document.querySelector('.orb-subtitle').textContent = 'Your voice-first AI companion';

orbBtn.setAttribute(
    'aria-pressed',
    'false'
);

orbLabel.textContent =
    'Tap to Speak';

if (conversationStatus) {

    conversationStatus.classList.remove(
        'listening'
    );

    conversationStatus.textContent =
        'Processing…';
}

if (conversationFooterText) {

    conversationFooterText.textContent =
        'Processing your question...';
}

    console.log("Microphone completely stopped.");
}

function openVoiceInterface() {

    // Save the previous completed exchange
    if (userTranscript.trim()) {
        conversationHistory.push({
            role: "user",
            text: userTranscript
        });
    }

    if (assistantTranscript.trim()) {
        conversationHistory.push({
            role: "assistant",
            text: assistantTranscript
        });
    }

    // Start a fresh current turn
    userTranscript = "";
    assistantTranscript = "";

    heroInner.classList.add('voice-active');

    voiceConversation.classList.add('active');

    if (conversationPlaceholder) {
        conversationPlaceholder.style.display = 'none';
    }

    conversationStatus.textContent =
        'Listening';

    conversationStatus.classList.add(
        'listening'
    );

    conversationFooterText.textContent =
        'Listening to you...';
}

orbBtn.addEventListener('click', async () => {

    // Move orb to center and open conversation UI
    if (voiceStage) {
        voiceStage.classList.add('voice-active');
    }

    if (orbBtn.classList.contains('listening')) {
        microphoneRequestId += 1;
        stopMicrophone();
        return;
    }

	const requestId = ++microphoneRequestId;
	orbBtn.classList.add('listening');

    document.querySelector('.orb-title').textContent = 'Listening...';
    document.querySelector('.orb-subtitle').textContent = 'Speak now';

	orbBtn.setAttribute('aria-pressed', 'true');
	orbLabel.textContent = 'Listening…';
    openVoiceInterface();

	try {
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		if (requestId !== microphoneRequestId || !orbBtn.classList.contains('listening')) {
			stream.getTracks().forEach(track => track.stop());
			return;
		}

		microphoneStream = stream;
		console.log('Microphone access granted');
		connectToSamarth();
	} catch (error) {
		if (requestId === microphoneRequestId) {
			stopMicrophone();
			console.error('Microphone access was denied or unavailable:', error);
		}
	}
});

// Temporary backend connection test
async function testBackendConnection() {
	try {
		const response = await fetch('http://127.0.0.1:8000/health');
		if (!response.ok) {
			throw new Error(`Backend returned HTTP ${response.status}`);
		}

		const data = await response.json();
		console.log('Backend health response:', data);
		console.log('Backend connection successful.');
	} catch (error) {
		console.error('Backend connection failed. Make sure the FastAPI server is running:', error);
	}
}

testBackendConnection();

// ----------------------------------------
// Gemini Live WebSocket test
// ----------------------------------------

function startMicrophoneProcessing() {

    if (!microphoneStream) {
        console.error("No microphone stream available.");
        return;
    }

    // Create microphone audio context
    micAudioContext = new AudioContext({
        sampleRate: 16000
    });

    // Create playback audio context only once
    if (!playbackContext) {
        playbackContext = new AudioContext({
            sampleRate: 24000
        });
    }

    micAudioContext.resume();
    playbackContext.resume();

    // Create microphone source
    micSource = micAudioContext.createMediaStreamSource(
        microphoneStream
    );

    // Process microphone audio
    micProcessor = micAudioContext.createScriptProcessor(
        4096,
        1,
        1
    );

    let micChunkCount = 0;

micProcessor.onaudioprocess = (event) => {

    micChunkCount++;

    if (micChunkCount <= 5) {
        console.log(
            "MIC AUDIO CALLBACK:",
            micChunkCount,
            "WebSocket state:",
            ws ? ws.readyState : "NO WS"
        );
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn(
            "Microphone callback fired, but WebSocket is not OPEN."
        );
        return;
    }

    const inputData =
        event.inputBuffer.getChannelData(0);

        // Convert Float32 audio to Int16 PCM
        const pcmData =
            new Int16Array(inputData.length);

        for (let i = 0; i < inputData.length; i++) {

            let sample = inputData[i];

            sample = Math.max(-1, Math.min(1, sample));

            pcmData[i] =
                sample < 0
                    ? sample * 0x8000
                    : sample * 0x7FFF;
        }

        // Send raw PCM audio to FastAPI
        console.log(
            "SENDING PCM AUDIO:",
            pcmData.byteLength,
            "bytes | WS state:",
            ws.readyState
        );
        
        ws.send(pcmData.buffer);
    };

    micSource.connect(micProcessor);

    // Required connection for ScriptProcessorNode
    micProcessor.connect(
        micAudioContext.destination
    );

    if (ws && ws.readyState === WebSocket.OPEN) {
        const activityStartMessage = JSON.stringify({
            activity_start: true
        });
    
        console.log(
            "SENDING ACTIVITY_START:",
            activityStartMessage,
            "| WS state:",
            ws.readyState
        );
    
        ws.send(activityStartMessage);
    
        console.log("ACTIVITY_START SENT.");
    }

    console.log(
        "Microphone audio streaming to Gemini..."
    );
}


function connectToSamarth() {

    // If WebSocket is already connected,
    // DO NOT create another one.
    if (ws && ws.readyState === WebSocket.OPEN) {

        console.log(
            "Existing WebSocket reused — keeping conversation alive."
        );

        startMicrophoneProcessing();
        return;
    }

    // If a connection is already being established,
    // wait for onopen.
    if (ws && ws.readyState === WebSocket.CONNECTING) {

        console.log(
            "WebSocket is already connecting..."
        );

        return;
    }

    console.log(
        "Creating new WebSocket connection to Samarth..."
    );

    ws = new WebSocket(
        "ws://127.0.0.1:8000/ws/voice"
    );

    ws.binaryType = "arraybuffer";

    ws.onopen = async () => {

        console.log(
            "WebSocket connected to Samarth!"
        );

        startMicrophoneProcessing();
    };


    ws.onmessage = async (event) => {

        // JSON message from FastAPI
        if (typeof event.data === "string") {

            try {

                const message =
                    JSON.parse(event.data);

                console.log(
                    "Message from Samarth:",
                    message
                );


                if (message.type === "connected") {

                    console.log(
                        "Gemini Live is ready!"
                    );
                }


                if (message.type === "transcript") {

                    userTranscript += message.text;

                    console.log(
                        "You said:",
                        userTranscript
                    );

                    renderConversation();
                }


                if (message.type === "assistant_transcript") {

                    assistantTranscript += message.text;

                    console.log(
                        "Samarth:",
                        assistantTranscript
                    );

                    renderConversation();
                }


                if (conversationStatus) {

                    conversationStatus.classList.remove(
                        "listening"
                    );

                    conversationStatus.classList.add(
                        "speaking"
                    );

                    conversationStatus.textContent =
                        "Samarth is speaking";
                }


                if (conversationFooterText) {

                    conversationFooterText.textContent =
                        "Samarth is speaking...";
                }


                if (message.type === "tool_call") {

                    console.log(
                        "Samarth is searching knowledge base:",
                        message.query
                    );

                    if (conversationStatus) {

                        conversationStatus.classList.remove(
                            "listening",
                            "speaking"
                        );

                        conversationStatus.textContent =
                            "Checking knowledge";
                    }


                    if (conversationFooterText) {

                        conversationFooterText.textContent =
                            "Searching Samarth's knowledge base...";
                    }
                }


                if (message.type === "error") {

                    console.error(
                        "Gemini error:",
                        message.message
                    );
                }


            } catch (error) {

                console.log(
                    "Received text:",
                    event.data
                );
            }

            return;
        }


        // Binary audio from Gemini
        if (event.data instanceof ArrayBuffer) {

            console.log(
                "Received Gemini audio:",
                event.data.byteLength,
                "bytes"
            );

            samarthIsSpeaking = true;

            await playGeminiAudio(event.data);
        }
    };


    ws.onerror = (error) => {

        console.error(
            "WebSocket error:",
            error
        );
    };


    ws.onclose = () => {

        console.log(
            "WebSocket connection closed."
        );

        ws = null;
    };
}

async function playGeminiAudio(arrayBuffer) {

    if (!playbackContext) {
        return;
    }

    const pcmData =
        new Int16Array(arrayBuffer);

    const audioBuffer =
        playbackContext.createBuffer(
            1,
            pcmData.length,
            24000
        );

    const channelData =
        audioBuffer.getChannelData(0);

    for (let i = 0; i < pcmData.length; i++) {

        channelData[i] =
            pcmData[i] / 32768;
    }

    const source =
        playbackContext.createBufferSource();

    source.buffer = audioBuffer;

    source.connect(
        playbackContext.destination
    );

    const currentTime =
        playbackContext.currentTime;

    if (nextPlayTime < currentTime) {
        nextPlayTime = currentTime;
    }

    source.start(nextPlayTime);

nextPlayTime += audioBuffer.duration;

// Mark Samarth as finished after all currently queued audio plays.
const finishTime = nextPlayTime;
const delay = Math.max(
    0,
    (finishTime - playbackContext.currentTime) * 1000
);

setTimeout(() => {

    if (playbackContext.currentTime >= finishTime - 0.05) {
        samarthIsSpeaking = false;

        console.log("Samarth finished speaking.");
    }

}, delay);

}