import { useRef, useState } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import { captureCanvas } from './utils/canvasUtils';

// Import Excalidraw styles
import '@excalidraw/excalidraw/index.css';
import './App.css';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

function App() {
  const excalidrawRef = useRef<ExcalidrawImperativeAPI | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState<string>('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Start recording user's voice
  const startRecording = async () => {
    try {
      setStatus('Starting microphone...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        await processRecording();
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatus('🎙️ Listening... Click again to send');
    } catch (error) {
      console.error('Microphone error:', error);
      setStatus('❌ Microphone access denied');
      setTimeout(() => setStatus(''), 3000);
    }
  };

  // Stop recording and process
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus('Processing...');
    }
  };

  // Process the recording with canvas context
  const processRecording = async () => {
    setIsProcessing(true);
    setStatus('📸 Capturing canvas...');

    try {
      // Capture canvas as context
      let canvasBase64 = '';
      if (excalidrawRef.current) {
        canvasBase64 = await captureCanvas(excalidrawRef.current, 'high');
      }

      // Convert audio to base64
      setStatus('🔄 Sending to ARIS...');
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const audioBase64 = await blobToBase64(audioBlob);

      // Send to backend
      const response = await fetch(`${BACKEND_URL}/talk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audio: audioBase64,
          canvas_image: canvasBase64
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      setStatus('🔊 ARIS is responding...');

      // Play audio response
      if (data.audio) {
        const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
        audio.onended = () => setStatus('');
        audio.onerror = () => setStatus('');
        await audio.play();
      } else {
        setStatus(data.text || 'No response from ARIS');
        setTimeout(() => setStatus(''), 5000);
      }

    } catch (error) {
      console.error('Processing error:', error);
      setStatus(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setTimeout(() => setStatus(''), 5000);
    } finally {
      setIsProcessing(false);
    }
  };

  // Toggle recording
  const handleTalkClick = () => {
    if (isRecording) {
      stopRecording();
    } else if (!isProcessing) {
      startRecording();
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* Talk to ARIS Button */}
      <div className="control-panel">
        <button
          className={`control-btn talk-btn ${isRecording ? 'active' : ''} ${isProcessing ? 'processing' : ''}`}
          onClick={handleTalkClick}
          disabled={isProcessing}
        >
          <span className="icon">{isRecording ? '⏹️' : '🎙️'}</span>
          {isRecording ? 'Stop & Send' : isProcessing ? 'Processing...' : 'Talk to ARIS'}
        </button>
      </div>

      {/* Status Indicator */}
      {status && (
        <div className="status-bar">
          {status}
        </div>
      )}

      {/* Excalidraw Canvas */}
      <div className="excalidraw-wrapper">
        <Excalidraw
          excalidrawAPI={(api) => {
            excalidrawRef.current = api;
          }}
          theme="dark"
        />
      </div>
    </div>
  );
}

// Helper function
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      const base64 = result.split(',')[1] || '';
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export default App;
