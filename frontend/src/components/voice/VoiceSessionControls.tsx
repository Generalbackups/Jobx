// frontend/src/components/voice/VoiceSessionControls.tsx
//
// Start Session, End Session, and Mute/Unmute controls.
// Buttons are disabled when state does not permit the action.

import React from 'react';
import { useVoiceAssistant } from '../../contexts/VoiceAssistantContext';

export function VoiceSessionControls() {
  const { sessionState, isMicMuted, startSession, endSession, toggleMic } =
    useVoiceAssistant();

  const isIdle    = sessionState === 'idle' || sessionState === 'ended' || sessionState === 'error';
  const isActive  = sessionState === 'active';
  const isBusy    = sessionState === 'connecting' || sessionState === 'ending';

  return (
    <div className="va-controls" role="group" aria-label="Voice assistant controls">
      {/* Start Session — shown when idle, ended, or error */}
      {isIdle && (
        <button
          className="va-btn va-btn--start"
          onClick={startSession}
          disabled={isBusy}
          aria-label="Start voice assistant session"
        >
          🎙 Start Voice Assistant
        </button>
      )}

      {/* Connecting state — non-interactive */}
      {isBusy && (
        <button className="va-btn va-btn--busy" disabled aria-busy="true">
          {sessionState === 'connecting' ? 'Connecting...' : 'Ending session...'}
        </button>
      )}

      {/* Active state controls */}
      {isActive && (
        <>
          <button
            className={['va-btn', isMicMuted ? 'va-btn--muted' : 'va-btn--mic'].join(' ')}
            onClick={toggleMic}
            aria-label={isMicMuted ? 'Unmute microphone' : 'Mute microphone'}
            aria-pressed={isMicMuted}
          >
            {isMicMuted ? '🔇 Unmute' : '🎤 Mute'}
          </button>
          <button
            className="va-btn va-btn--end"
            onClick={endSession}
            aria-label="End voice assistant session"
          >
            ✕ End Session
          </button>
        </>
      )}
    </div>
  );
}
