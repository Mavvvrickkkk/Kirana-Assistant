import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export function useVoice() {
  const [isRecording, setIsRecording] = useState(false);
  const [proposal, setProposal] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-IN'; // Works well for Hinglish/Telugu code-mixing

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        processText(transcript);
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          alert("Microphone access is blocked! If you are in an embedded preview (like VS Code), Voice won't work. Please open http://localhost:5173 in a regular Chrome/Edge tab.");
          recognitionRef.current = null; // Force fallback next time
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const stopRecording = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop();
    }
    setIsRecording(false);
  };

  const startRecording = async () => {
    setProposal(null);
    if (recognitionRef.current && recognitionRef.current.constructor.name !== 'MediaRecorder') {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (e) {
        console.error(e);
        if (e.name === 'NotAllowedError') {
          alert("Microphone blocked. Please open this app in a full browser tab.");
        }
      }
    } else {
      // Fallback to MediaRecorder for environments without Web Speech API
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);

        mediaRecorder.onstop = async () => {
          setIsProcessing(true);
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append('file', audioBlob, 'command.webm');

          try {
            const res = await axios.post(`${API_BASE}/voice/process`, formData);
            setProposal(res.data);
          } catch (e) {
            console.error(e);
            alert("Error processing command: " + (e.response?.data?.detail || e.message));
          } finally {
            setIsProcessing(false);
          }
        };

        // Attach to the ref so stopRecording can access it
        recognitionRef.current = mediaRecorder;
        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        alert("Microphone permission denied! If you are using VS Code Preview, please open http://localhost:5173 in a real Chrome browser window.");
      }
    }
  };

  const processText = async (text) => {
    setIsProcessing(true);
    setProposal(null);
    try {
      const formData = new FormData();
      formData.append('text', text);
      const res = await axios.post(`${API_BASE}/voice/process`, formData);
      setProposal(res.data);
    } catch (e) {
      console.error(e);
      alert("Error processing command: " + (e.response?.data?.detail || e.message));
    } finally {
      setIsProcessing(false);
    }
  };

  return {
    isRecording,
    isProcessing,
    proposal,
    setProposal,
    startRecording,
    stopRecording,
    processText
  };
}