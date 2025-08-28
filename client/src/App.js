// src/App.js
import React, { useState, useRef } from 'react';
import { AudioRecorder, useAudioRecorder } from 'react-audio-voice-recorder';
import axios from 'axios';
import './styles.css';

function App() {
  const [userID, setUserID] = useState('user_001');
  const [messages, setMessages] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const audioRef = useRef(null);

  const recorderControls = useAudioRecorder(
    {
      noiseSuppression: true,
      echoCancellation: true,
    },
    (err) => console.error("Recorder error:", err)
  );

  // Handle recorded audio
  const handleRecordingComplete = async (blob) => {
    setIsRecording(false);

    const file = new File([blob], "recording.wav", { type: "audio/wav" });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userID);
    formData.append('generate_audio', 'true');

    try {
      const res = await axios.post('http://localhost:8000/voice/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const aiReply = res.data.response;
      const audioURL = res.data.audio_url; // e.g., "/static/audio/xyz.mp3"

      // Add to chat
      setMessages((prev) => [
        ...prev,
        { type: 'user', text: '🎤 Voice message sent' },
        { type: 'ai', text: aiReply, audio: audioURL },
      ]);

      // Play AI response
      if (audioURL && audioRef.current) {
        audioRef.current.src = `http://localhost:8000${audioURL}`;
        audioRef.current.play().catch(e => console.error("Audio play failed:", e));
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { type: 'user', text: '🎤 Voice message sent' },
        { type: 'ai', text: "Sorry, I couldn't process your request." }
      ]);
    }
  };

  return (
    <div className="App">
      <h1>🎙️ SmartFlow Voice Chat</h1>

      <div className="setup">
        <input
          type="text"
          placeholder="Enter User ID"
          value={userID}
          onChange={(e) => setUserID(e.target.value)}
        />
      </div>

      <div className="chat">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.type}`}>
            <p>{msg.text}</p>
            {msg.audio && <audio src={msg.audio} controls />}
          </div>
        ))}
      </div>

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
          silenceDetection={true} // 🔥 Auto-stop on silence!
          stopRecordingOnSilence={true} // Stops after ~1.5s of silence
          stopRecordingOnPress={false} // Let silence stop it
          classes={{
            button: 'record-button',
            container: 'recorder-container',
            visualizer: 'visualizer'
          }}
        />
        <p className="status">
          {isRecording ? 'Speak now... I’ll stop when you pause.' : 'Hold to talk'}
        </p>
      </div>

      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

export default App;