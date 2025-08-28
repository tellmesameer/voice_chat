# services/vad.py
import webrtcvad
import collections
import pydub
from pydub import AudioSegment
import io

class Frame:
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration

def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio."""
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0
    duration = (n / 2) / sample_rate
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n

def vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, vad, frames):
    """Collects speech segments using VAD."""
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                for f, _ in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                ring_buffer.clear()
                yield b''.join([f.bytes for f in voiced_frames])
                voiced_frames = []
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])

def detect_speech_segments(wav_data, sample_rate=16000, aggressiveness=2):
    """Returns chunks of audio that contain speech."""
    vad = webrtcvad.Vad(aggressiveness)
    audio = AudioSegment.from_wav(io.BytesIO(wav_data)).set_frame_rate(sample_rate).set_channels(1)
    raw_data = audio.raw_data

    frames = frame_generator(30, raw_data, sample_rate)
    frames = list(frames)
    segments = vad_collector(sample_rate, 30, 300, vad, frames)
    return segments