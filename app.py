# app.py
import streamlit as st
import requests
import pyaudio
import wave
import os
import uuid
import threading
import time

# === Configuration ===
BACKEND_URL = "http://localhost:8000"
USER_ID = st.session_state.get("user_id", "user_001")  # Allow user to set ID

# === Sidebar: User ID Input ===
with st.sidebar:
    st.header("🎙️ Voice Chat Settings")
    USER_ID = st.text_input("User ID", value=USER_ID, key="user_id_input")
    st.session_state.user_id = USER_ID
    st.markdown(f"**Current User ID:** `{USER_ID}`")

# === Page Setup ===
st.title("🎙️ SmartFlow Voice Chat")
st.markdown("Click the button to start speaking. Click again to stop and send.")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "audio_file_path" not in st.session_state:
    st.session_state.audio_file_path = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# === Audio Settings ===
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
WAVE_OUTPUT_DIR = "temp_audio"
os.makedirs(WAVE_OUTPUT_DIR, exist_ok=True)

p = pyaudio.PyAudio()

# === Recording Function (runs in thread) ===
def record_audio():
    st.session_state.is_recording = True
    audio_file_path = os.path.join(WAVE_OUTPUT_DIR, f"temp_{uuid.uuid4().hex}.wav")
    st.session_state.audio_file_path = audio_file_path

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []
    st.write("🔴 **Recording... (Click 'Stop' to finish)**")

    while st.session_state.is_recording:
        data = stream.read(CHUNK)
        frames.append(data)
        # Small sleep to prevent UI freeze
        time.sleep(0.01)

    stream.stop_stream()
    stream.close()

    wf = wave.open(audio_file_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    st.write(f"✅ Saved to {audio_file_path}")

# === Toggle Recording Button ===
if st.button("🔴 Start Recording" if not st.session_state.is_recording else "🛑 Stop Recording"):
    if not st.session_state.is_recording:
        # Start recording in a new thread
        recording_thread = threading.Thread(target=record_audio, daemon=True)
        recording_thread.start()
    else:
        # Stop recording
        st.session_state.is_recording = False
        st.rerun()

# === Process After Recording ===
if st.session_state.audio_file_path and not st.session_state.is_recording:
    audio_file_path = st.session_state.audio_file_path

    with st.spinner("📤 Uploading and processing..."):
        try:
            with open(audio_file_path, "rb") as f:
                files = {"file": (os.path.basename(audio_file_path), f, "audio/wav")}
                data = {"user_id": USER_ID}

                response = requests.post(f"{BACKEND_URL}/voice/upload", files=files, data=data)

            if response.status_code == 200:
                result = response.json()

                # Add to chat history
                st.session_state.messages.append({
                    "role": "user",
                    "content": "🎤 Voice message sent"
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"]
                })

                # Clean up file
                os.remove(audio_file_path)
                st.session_state.audio_file_path = None

                # Rerun to update chat
                st.rerun()
            else:
                st.error(f"❌ API Error: {response.status_code} - {response.text}")
                st.session_state.audio_file_path = None  # Reset on error

        except Exception as e:
            st.error(f"❌ Failed to connect to backend: {str(e)}")
            st.session_state.audio_file_path = None

# === Optional: Text Input Fallback ===
if prompt := st.chat_input("Or type your message..."):
    with st.spinner("AI is thinking..."):
        try:
            resp = requests.post(f"{BACKEND_URL}/chat/send", json={"user_id": USER_ID, "message": prompt})
            if resp.status_code == 200:
                result = resp.json()
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.session_state.messages.append({"role": "assistant", "content": result["response"]})
            else:
                st.error("Failed to get response.")
        except Exception as e:
            st.error(f"Connection error: {e}")