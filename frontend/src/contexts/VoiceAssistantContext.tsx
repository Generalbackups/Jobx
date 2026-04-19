// frontend/src/contexts/VoiceAssistantContext.tsx

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  ReactNode,
} from 'react';
import { Room, RoomEvent, ConnectionState, DataPacket_Kind } from 'livekit-client';
import {
  type VoiceAssistantContextValue,
  type VoiceSessionState,
  type TranscriptEntry,
  type JobPostingFormData,
  type InboundDataMessage,
} from '../types/voice-assistant';

// ── Read LIVEKIT_URL from env ─────────────────────────────────────────────────
// Vite projects: import.meta.env.VITE_LIVEKIT_URL
// CRA projects:  process.env.REACT_APP_LIVEKIT_URL
// Detect which one is available and use it. Throw at module load time if missing
// so the developer sees the error immediately rather than at connection time.
const LIVEKIT_WS_URL: string = (() => {
  // @ts-ignore — one of these will exist depending on build tool
  const url = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_LIVEKIT_URL)
    || (typeof process !== 'undefined' && process.env?.REACT_APP_LIVEKIT_URL);
  if (!url) {
    throw new Error(
      'LiveKit URL not configured. Set VITE_LIVEKIT_URL (Vite) or REACT_APP_LIVEKIT_URL (CRA) in your .env file.'
    );
  }
  return url;
})();

// ── Context definition ────────────────────────────────────────────────────────
const VoiceAssistantContext = createContext<VoiceAssistantContextValue | null>(null);

// ── Room instance ─────────────────────────────────────────────────────────────
// The Room is created ONCE outside the component tree so it persists across
// re-renders. Creating it inside the component would cause a new Room object
// on every render, breaking the connection.
const room = new Room({
  adaptiveStream: true,
  dynacast: true,
  disconnectOnPageLeave: true,  // automatically disconnects if browser tab is closed
});

// ── Provider component ────────────────────────────────────────────────────────
interface VoiceAssistantProviderProps {
  children: ReactNode;
  // Callback fired whenever a field value changes via voice.
  // The parent form uses this to sync form state.
  onFieldUpdate?: (field: keyof JobPostingFormData, value: any) => void;
  // Callback fired when the session ends with final complete data.
  onSessionComplete?: (jobData: JobPostingFormData) => void;
}

export function VoiceAssistantProvider({
  children,
  onFieldUpdate,
  onSessionComplete,
}: VoiceAssistantProviderProps) {
  const [sessionState, setSessionState] = useState<VoiceSessionState>('idle');
  const [collectedFields, setCollectedFields] = useState<Partial<JobPostingFormData>>({});
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Keep a ref to onFieldUpdate so the DataChannel handler always has the latest
  // version without needing to be re-registered on every render.
  const onFieldUpdateRef = useRef(onFieldUpdate);
  onFieldUpdateRef.current = onFieldUpdate;
  const onSessionCompleteRef = useRef(onSessionComplete);
  onSessionCompleteRef.current = onSessionComplete;

  // ── Room event listeners ────────────────────────────────────────────────────
  // Register once. These run for the lifetime of the provider.
  useEffect(() => {
    function handleDisconnected() {
      // Only transition to "ended" if we were active/ending — not on error disconnects
      setSessionState((prev) =>
        prev === 'active' || prev === 'ending' ? 'ended' : prev
      );
    }

    function handleConnectionStateChanged(state: ConnectionState) {
      if (state === ConnectionState.Reconnecting) {
        // Show reconnecting state without wiping collected data
        console.warn('[VoiceAssistant] Room reconnecting...');
      }
    }

    function handleActiveSpeakersChanged(speakers: any[]) {
      // Detect if the remote agent participant is in the active speakers list.
      // The agent's identity is "job-posting-agent" (set in agent_worker.py).
      const agentIsSpeaking = speakers.some(
        (p) => p.identity === 'job-posting-agent'
      );
      setIsAgentSpeaking(agentIsSpeaking);
    }

    room.on(RoomEvent.Disconnected, handleDisconnected);
    room.on(RoomEvent.ConnectionStateChanged, handleConnectionStateChanged);
    room.on(RoomEvent.ActiveSpeakersChanged, handleActiveSpeakersChanged);

    return () => {
      room.off(RoomEvent.Disconnected, handleDisconnected);
      room.off(RoomEvent.ConnectionStateChanged, handleConnectionStateChanged);
      room.off(RoomEvent.ActiveSpeakersChanged, handleActiveSpeakersChanged);
    };
  }, []);

  // ── DataChannel message handler ─────────────────────────────────────────────
  // Registered once. Listens for all messages from the agent on the
  // "job_posting_updates" topic. This is where field updates and session
  // completion are processed.
  useEffect(() => {
    function handleDataReceived(
      payload: Uint8Array,
      participant: any,
      _kind: any,
      topic?: string,
    ) {
      // Only process messages on the correct topic
      if (topic !== 'job_posting_updates') return;

      let message: InboundDataMessage;
      try {
        message = JSON.parse(new TextDecoder().decode(payload)) as InboundDataMessage;
      } catch {
        console.error('[VoiceAssistant] Failed to parse DataChannel message');
        return;
      }

      switch (message.type) {
        case 'field_update': {
          // Update the local collectedFields state
          setCollectedFields((prev) => ({
            ...prev,
            [message.field]: message.value,
          }));
          // Notify the parent form so it can sync the field into its own state
          onFieldUpdateRef.current?.(message.field, message.value);
          break;
        }

        case 'session_complete': {
          // Full final snapshot — set all fields at once
          setCollectedFields(message.job_data);
          onSessionCompleteRef.current?.(message.job_data);
          setSessionState('ended');
          break;
        }

        case 'agent_state': {
          // Optional: use for advanced UI indicators
          console.info('[VoiceAssistant] Agent state:', message.state);
          break;
        }

        case 'session_error': {
          setErrorMessage(message.message);
          setSessionState('error');
          break;
        }

        default:
          console.warn('[VoiceAssistant] Unknown message type:', (message as any).type);
      }
    }

    room.on(RoomEvent.DataReceived, handleDataReceived);
    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, []);

  // ── startSession ────────────────────────────────────────────────────────────
  const startSession = useCallback(async () => {
    // Reset state from any previous session
    setErrorMessage(null);
    setCollectedFields({});
    setTranscript([]);
    setSessionState('connecting');

    try {
      // Step 1: Request microphone permission FIRST (fail fast before any API calls)
      // If the user denies permission, we want to show the error immediately
      // without having created a session on the backend.
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err: any) {
      const isDenied = err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError';
      setErrorMessage(
        isDenied
          ? 'Microphone access denied. Please allow microphone access in your browser settings and try again.'
          : 'Could not access your microphone. Please check your device settings.'
      );
      setSessionState('error');
      return; // Do NOT proceed to API call if mic is unavailable
    }

    let token: string;
    let roomName: string;

    try {
      // Step 2: Get token from FastAPI backend
      // The backend creates the session record and returns a signed LiveKit JWT
      // with agent dispatch embedded. user_id must come from the app's auth context.
      // IMPORTANT: Replace 'current_user_id_placeholder' with the actual
      // authenticated user's ID from your app's auth system.
      const response = await fetch('/api/voice/start-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          // TODO(post-verification): replace current_user_id_placeholder with the real auth user ID from app auth context/store.
          user_id: 'current_user_id_placeholder',
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}: ${await response.text()}`);
      }

      const data = await response.json();
      token = data.token;
      roomName = data.room_name;

    } catch (err: any) {
      console.error('[VoiceAssistant] Failed to get session token:', err);
      setErrorMessage('Failed to start voice session. Please try again.');
      setSessionState('error');
      return;
    }

    try {
      // Step 3: Connect to LiveKit room using the JWT from the backend.
      // The token already embeds agent dispatch — LiveKit Cloud will automatically
      // dispatch the agent worker to this room when the first participant connects.
      await room.connect(LIVEKIT_WS_URL, token, {
        autoSubscribe: true,  // subscribe to all remote tracks (agent audio) automatically
      });

      // Step 4: Enable the local microphone track.
      // This must happen AFTER room.connect() — enabling before connection fails silently.
      await room.localParticipant.setMicrophoneEnabled(true);
      setIsMicMuted(false);

      setSessionState('active');
      console.info('[VoiceAssistant] Session active | room:', roomName);

    } catch (err: any) {
      console.error('[VoiceAssistant] Failed to connect to LiveKit room:', err);
      setErrorMessage('Failed to connect to the voice session. Please try again.');
      setSessionState('error');
      // Attempt cleanup in case room is in a partial state
      try { await room.disconnect(); } catch {}
    }
  }, []);

  // ── endSession ──────────────────────────────────────────────────────────────
  const endSession = useCallback(() => {
    if (sessionState !== 'active') return;
    setSessionState('ending');

    // Step 1: Send end_session DataChannel message to the agent.
    // The agent receives this and calls its finalize_session tool,
    // which will send the session_complete DataChannel message back to us,
    // then disconnect from the room.
    try {
      const payload = new TextEncoder().encode(JSON.stringify({ type: 'end_session' }));
      room.localParticipant.publishData(payload, {
        reliable: true,
        topic: 'job_posting_updates',  // must match agent's DataChannel topic
      });
    } catch (err) {
      console.error('[VoiceAssistant] Failed to send end_session message:', err);
    }

    // Step 2: Fallback disconnect after 6 seconds if the agent does not send
    // session_complete within that time. This ensures the user is never
    // stuck in "ending" state due to an unresponsive agent.
    setTimeout(async () => {
      if (room.state !== ConnectionState.Disconnected) {
        console.warn('[VoiceAssistant] Agent did not respond to end_session — force disconnecting.');
        await room.disconnect();
        setSessionState('ended');
      }
    }, 6000);
  }, [sessionState]);

  // ── toggleMic ───────────────────────────────────────────────────────────────
  const toggleMic = useCallback(async () => {
    if (sessionState !== 'active') return;
    const newMutedState = !isMicMuted;
    await room.localParticipant.setMicrophoneEnabled(!newMutedState);
    setIsMicMuted(newMutedState);
  }, [sessionState, isMicMuted]);

  // ── Transcription listener ──────────────────────────────────────────────────
  // LiveKit Agents SDK publishes STT transcriptions as room transcription events.
  // We listen to these to build the conversation transcript shown to the user.
  useEffect(() => {
    function handleTranscription(
      segments: any[],
      participant: any,
    ) {
      if (!segments || segments.length === 0) return;

      const role: 'agent' | 'user' =
        participant?.identity === 'job-posting-agent' ? 'agent' : 'user';

      segments.forEach((segment: any) => {
        if (!segment.text?.trim()) return;

        const entry: TranscriptEntry = {
          id: segment.id || `${Date.now()}-${Math.random()}`,
          role,
          content: segment.text,
          timestamp: Date.now(),
          isFinal: segment.final ?? segment.isFinal ?? true,
        };

        setTranscript((prev) => {
          // Update existing entry if same id (partial → final update)
          const existingIndex = prev.findIndex((e) => e.id === entry.id);
          if (existingIndex !== -1) {
            const updated = [...prev];
            updated[existingIndex] = entry;
            return updated;
          }
          return [...prev, entry];
        });
      });
    }

    room.on(RoomEvent.TranscriptionReceived, handleTranscription);
    return () => {
      room.off(RoomEvent.TranscriptionReceived, handleTranscription);
    };
  }, []);

  const value: VoiceAssistantContextValue = {
    sessionState,
    collectedFields,
    transcript,
    isAgentSpeaking,
    isMicMuted,
    errorMessage,
    startSession,
    endSession,
    toggleMic,
  };

  return (
    <VoiceAssistantContext.Provider value={value}>
      {children}
    </VoiceAssistantContext.Provider>
  );
}

// ── Consumer hook ─────────────────────────────────────────────────────────────
export function useVoiceAssistant(): VoiceAssistantContextValue {
  const context = useContext(VoiceAssistantContext);
  if (!context) {
    throw new Error(
      'useVoiceAssistant must be used inside <VoiceAssistantProvider>. ' +
      'Wrap the job posting page with <VoiceAssistantProvider>.'
    );
  }
  return context;
}

// Export room for use in components that need direct room access (e.g. RoomAudioRenderer)
export { room };
