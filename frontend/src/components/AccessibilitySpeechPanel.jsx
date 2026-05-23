import { useState, useRef } from 'react';
import { Mic, MicOff, X, Copy } from 'lucide-react';
import { chatAPI, handleAPIError } from '../api/api';
import toast from 'react-hot-toast';

const AccessibilitySpeechPanel = ({ open, onClose }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const stopTracks = () => {
    if (mediaRecorderRef.current?.stream) {
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
    }
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      toast.error('Your browser does not support audio recording.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        stopTracks();
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (!blob.size) {
          toast.error('No audio captured. Please try again.');
          return;
        }

        try {
          setLoading(true);
          const response = await chatAPI.speechToText(blob);
          const text = response.data?.text || '';
          if (text) {
            setTranscript(text);
          } else {
            toast.error('Could not understand the audio.');
          }
        } catch (error) {
          handleAPIError(error);
        } finally {
          setLoading(false);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      toast.error('Microphone access denied or unavailable.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const copyTranscript = async () => {
    if (!transcript) return;
    try {
      await navigator.clipboard.writeText(transcript);
      toast.success('Copied to clipboard');
    } catch {
      toast.error('Could not copy text');
    }
  };

  if (!open) return null;

  return (
    <div
      className="a11y-widget-root fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onClick={onClose}
      data-asl-skip
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
        data-asl-skip
        role="dialog"
        aria-labelledby="a11y-stt-title"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 id="a11y-stt-title" className="text-lg font-bold text-gray-900">
            Speech to Text
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 focus:ring-2 focus:ring-accent"
            aria-label="Close speech to text"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="mb-4 text-sm text-gray-600">
          Record your voice. Text appears below — copy it anywhere on the site.
        </p>

        <div className="mb-4 flex justify-center">
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading}
            className={`flex items-center gap-2 rounded-full px-6 py-3 font-medium text-white focus:ring-2 focus:ring-accent focus:ring-offset-2 ${
              isRecording ? 'bg-red-600 hover:bg-red-700' : 'bg-accent hover:bg-primary-700'
            }`}
            aria-pressed={isRecording}
          >
            {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            {loading ? 'Processing…' : isRecording ? 'Stop' : 'Start recording'}
          </button>
        </div>

        <label htmlFor="a11y-transcript" className="mb-1 block text-sm font-medium text-gray-700">
          Transcript
        </label>
        <textarea
          id="a11y-transcript"
          className="input-field min-h-[100px] resize-y"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Your speech will appear here…"
          readOnly={loading}
        />

        {transcript && (
          <button
            type="button"
            onClick={copyTranscript}
            className="mt-3 flex items-center gap-2 text-sm font-medium text-accent hover:underline focus:outline-none focus:ring-2 focus:ring-accent rounded"
          >
            <Copy className="h-4 w-4" />
            Copy to clipboard
          </button>
        )}
      </div>
    </div>
  );
};

export default AccessibilitySpeechPanel;
