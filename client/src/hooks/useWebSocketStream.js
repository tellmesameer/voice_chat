import { useRef, useEffect } from 'react';

export default function useWebSocketStream({ backendUrl, userID, onFinalResult, onError }) {
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const monitorIntervalRef = useRef(null);
  const awaitingResultRef = useRef(false);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ws = new WebSocket(`${backendUrl.replace('http', 'ws')}/voice/ws?user_id=${encodeURIComponent(userID)}`);
      ws.binaryType = 'arraybuffer';

      streamRef.current = stream;

      ws.onopen = () => {
        // Start MediaRecorder
        const options = { mimeType: 'audio/webm;codecs=opus' };
        const mr = new MediaRecorder(stream, options);
        mediaRecorderRef.current = mr;

        mr.ondataavailable = (e) => {
          if (e.data && e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        };

        mr.onstop = () => {
          try { ws.send(JSON.stringify({ event: 'stop' })); } catch (e) {}
        };

        mr.start(250);

        // setup analyser for silence detection
        try {
          audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
          const source = audioContextRef.current.createMediaStreamSource(stream);
          const analyser = audioContextRef.current.createAnalyser();
          analyser.fftSize = 512;
          source.connect(analyser);
          analyserRef.current = analyser;

          const bufferLength = analyser.frequencyBinCount;
          const data = new Uint8Array(bufferLength);
          const silenceThreshold = 0.01;
          const silenceDuration = 1000;

          monitorIntervalRef.current = setInterval(() => {
            analyser.getByteTimeDomainData(data);
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
              const v = (data[i] - 128) / 128;
              sum += v * v;
            }
            const rms = Math.sqrt(sum / bufferLength);
            if (rms < silenceThreshold) {
              if (!silenceTimerRef.current) silenceTimerRef.current = Date.now();
              else if (Date.now() - silenceTimerRef.current >= silenceDuration) {
                try { if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') mediaRecorderRef.current.stop(); } catch (e) {}
                clearInterval(monitorIntervalRef.current); monitorIntervalRef.current = null;
              }
            } else {
              silenceTimerRef.current = null;
            }
          }, 200);
        } catch (e) {
          console.warn('Silence detection setup failed', e);
        }
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.ack) return;
          if (data.transcription || data.response || data.error) {
            onFinalResult && onFinalResult(data);
            awaitingResultRef.current = false;
            // cleanup
            try { streamRef.current && streamRef.current.getTracks().forEach(t => t.stop()); } catch (e) {}
            try { analyserRef.current && analyserRef.current.disconnect && analyserRef.current.disconnect(); } catch (e) {}
            try { audioContextRef.current && audioContextRef.current.close(); } catch (e) {}
            try { ws.close(); } catch (e) {}
            if (monitorIntervalRef.current) { clearInterval(monitorIntervalRef.current); monitorIntervalRef.current = null; }
            silenceTimerRef.current = null;
          }
        } catch (err) {
          onError && onError(err, evt.data);
        }
      };

      ws.onclose = () => {
        try { streamRef.current && streamRef.current.getTracks().forEach(t => t.stop()); } catch (e) {}
        try { analyserRef.current && analyserRef.current.disconnect && analyserRef.current.disconnect(); } catch (e) {}
        try { audioContextRef.current && audioContextRef.current.close(); } catch (e) {}
        if (monitorIntervalRef.current) { clearInterval(monitorIntervalRef.current); monitorIntervalRef.current = null; }
        silenceTimerRef.current = null;
        awaitingResultRef.current = false;
      };

      ws.onerror = (e) => onError && onError(e);
      wsRef.current = ws;
      return { ws, mediaRecorder: mediaRecorderRef.current };
    } catch (err) {
      onError && onError(err);
      throw err;
    }
  };

  const stop = () => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') mediaRecorderRef.current.stop();
    } catch (e) {}

    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ event: 'stop' }));
        awaitingResultRef.current = true;
        setTimeout(() => {
          if (awaitingResultRef.current) {
            try { wsRef.current && wsRef.current.close(); } catch (e) {}
            awaitingResultRef.current = false;
            try { streamRef.current && streamRef.current.getTracks().forEach(t => t.stop()); } catch (e) {}
            if (monitorIntervalRef.current) { clearInterval(monitorIntervalRef.current); monitorIntervalRef.current = null; }
          }
        }, 10000);
      }
    } catch (e) { onError && onError(e); }
  };

  useEffect(() => {
    return () => {
      try { mediaRecorderRef.current && mediaRecorderRef.current.stop(); } catch (e) {}
      try { wsRef.current && wsRef.current.close(); } catch (e) {}
    };
  }, []);

  return { start, stop };
}
