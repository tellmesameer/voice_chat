// src/App.js
import React, { useState, useRef } from 'react';
import { AudioRecorder, useAudioRecorder } from 'react-audio-voice-recorder';
import axios from 'axios';
import './styles.css';

// Backend URL
const BACKEND_URL = "http://localhost:8000";

function App() {
  const [userID, setUserID] = useState('user_001');
  const [messages, setMessages] = useState([]);
  const audioRef = useRef(null);

  // Setup recorder
  const recorderControls = useAudioRecorder(
    {
      noiseSuppression: true,
      echoCancellation: true,
    },
    (err) => console.error("Microphone error:", err)
  );

  // Handle recording completion
  const handleRecordingComplete = async (blob) => {
    const file = new File([blob], "recording.wav", { type: "audio/wav" });
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userID);
    formData.append('generate_audio', 'true');

    try {
      const res = await axios.post(`${BACKEND_URL}/voice/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      console.log("🎙️ API Response:", res.data);

      const aiReply = res.data.response || "I couldn't understand that.";
      const audioURL = res.data.audio_url || null;

      // Add user message (with blob for retry)
      setMessages(prev => [
        ...prev,
        { type: 'user', text: '🎤 Voice message sent', blob: blob },
        { type: 'ai', text: aiReply, audio: audioURL }
      ]);

      // Play AI audio if available
      if (audioURL && audioRef.current) {
        audioRef.current.src = `${BACKEND_URL}${audioURL}`;
        audioRef.current.play().catch(e => console.error("Audio playback failed:", e));
      }
    } catch (err) {
      console.error("❌ API Error:", err);
      setMessages(prev => [
        ...prev,
        { type: 'user', text: '🎤 Voice message sent' },
        { type: 'ai', text: "Sorry, I couldn't process your request." }
      ]);
    }
  };

  // Retry with the same audio blob
  const handleRetry = async (audioBlob) => {
    const file = new File([audioBlob], "retry.wav", { type: "audio/wav" });
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userID);
    formData.append('generate_audio', 'true');

    try {
      const res = await axios.post(`${BACKEND_URL}/voice/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const aiReply = res.data.response || "I couldn't understand that.";
      const audioURL = res.data.audio_url || null;

      setMessages(prev => [
        ...prev,
        { type: 'user', text: '🔁 Retried voice message', blob: audioBlob },
        { type: 'ai', text: aiReply, audio: audioURL }
      ]);

      if (audioURL && audioRef.current) {
        audioRef.current.src = `${BACKEND_URL}${audioURL}`;
        audioRef.current.play().catch(e => console.error("Audio playback failed:", e));
      }
    } catch (err) {
      console.error("❌ Retry failed:", err);
      setMessages(prev => [
        ...prev,
        { type: 'user', text: '🔁 Retried voice message' },
        { type: 'ai', text: "Sorry, I couldn't process your request." }
      ]);
    }
  };

  return (
    <div className="App">
      <h1>🎙️ SmartFlow Voice Chat</h1>

      {/* User ID Input */}
      <div className="setup">
        <input
          type="text"
          placeholder="Enter User ID"
          value={userID}
          onChange={(e) => setUserID(e.target.value)}
          style={{ padding: '10px', fontSize: '16px', borderRadius: '8px', border: '1px solid #ccc' }}
        />
      </div>

      {/* Chat History */}
      <div className="chat">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.type}`}>
            <p>{msg.text}</p>
            {msg.audio && (
              <div>
                <audio src={`${BACKEND_URL}${msg.audio}`} controls style={{ marginTop: '5px' }} />
              </div>
            )}
            {/* Retry Button for User Messages */}
            {msg.type === 'user' && (
              <button
                onClick={() => handleRetry(msg.blob)}
                style={{
                  background: '#e0e0e0',
                  border: 'none',
                  padding: '4px 8px',
                  fontSize: '12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  marginLeft: '8px',
                  opacity: 0.7,
                }}
                title="Retry with same audio"
              >
                🔁 Retry
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Audio Recorder */}
      <div className="mic-section">
        <AudioRecorder
          onRecordingComplete={handleRecordingComplete}
          recorderControls={recorderControls}
          audioTrackConstraints={{
            noiseSuppression: true,
            echoCancellation: true,
          }}
          onNotAllowedOrFound={(err) => console.error("Microphone error:", err)}
          downloadOnSavePress={false}
          downloadFileExtension="wav"
          mediaRecorderOptions={{
            audioBitsPerSecond: 128000,
          }}
          showVisualizer={true}
          silenceDetection={true}
          stopRecordingOnSilence={true}
          stopRecordingOnPress={false}
          classes={{
            button: 'record-button',
            container: 'recorder-container',
            visualizer: 'visualizer'
          }}
        />
        <p className="status">
          {recorderControls.isRecording ? '🔴 Speak now... I’ll stop when you pause.' : '🎤 Hold to talk'}
        </p>
      </div>

      {/* Hidden Audio Player */}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

export default App;