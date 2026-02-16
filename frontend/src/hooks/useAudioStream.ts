import { useState, useRef, useCallback, useEffect } from 'react';

interface UseAudioStreamReturn {
    startRecording: () => void;
    stopRecording: () => void;
    isRecording: boolean;
    isConnected: boolean;
    audioResponse: string | null;
    error: string | null;
}

/**
 * Custom hook for WebSocket-based audio streaming.
 * Handles microphone capture, streaming to backend, and receiving audio responses.
 * 
 * @param wsUrl - WebSocket endpoint URL for audio streaming
 * @returns Object with recording controls and state
 */
export function useAudioStream(wsUrl: string): UseAudioStreamReturn {
    const [isRecording, setIsRecording] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [audioResponse, setAudioResponse] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // Initialize WebSocket connection
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected for audio streaming');
                setIsConnected(true);
                setError(null);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.audio) {
                        setAudioResponse(data.audio);
                    }
                    if (data.text) {
                        console.log('ARIS response:', data.text);
                    }
                } catch (e) {
                    // If not JSON, might be raw audio data
                    console.log('Received non-JSON message');
                }
            };

            ws.onerror = (event) => {
                console.error('WebSocket error:', event);
                setError('Connection error. Mini-Omni2 may not be running.');
            };

            ws.onclose = () => {
                console.log('WebSocket closed');
                setIsConnected(false);
            };

            wsRef.current = ws;
        } catch (err) {
            console.error('Failed to create WebSocket:', err);
            setError('Failed to connect to audio streaming service.');
        }
    }, [wsUrl]);

    // Start recording from microphone
    const startRecording = useCallback(async () => {
        try {
            setError(null);

            // Connect WebSocket if not connected
            connectWebSocket();

            // Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });
            streamRef.current = stream;

            // Create MediaRecorder
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus',
            });
            mediaRecorderRef.current = mediaRecorder;

            // Send audio chunks to WebSocket
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
                    // Convert to base64 and send
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64 = (reader.result as string).split(',')[1];
                        wsRef.current?.send(JSON.stringify({
                            type: 'audio_chunk',
                            data: base64,
                        }));
                    };
                    reader.readAsDataURL(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                // Notify backend that recording has ended
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({ type: 'end_stream' }));
                }
            };

            // Start recording with 250ms chunks
            mediaRecorder.start(250);
            setIsRecording(true);
        } catch (err) {
            console.error('Failed to start recording:', err);
            setError('Microphone access denied. Please allow microphone access.');
        }
    }, [connectWebSocket]);

    // Stop recording
    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }

        setIsRecording(false);
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopRecording();
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [stopRecording]);

    return {
        startRecording,
        stopRecording,
        isRecording,
        isConnected,
        audioResponse,
        error,
    };
}
