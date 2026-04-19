// frontend/src/components/voice/VoiceSessionStatus.tsx
//
// Displays the current session state as a labelled badge.

import React from 'react';
import { useVoiceAssistant } from '../../contexts/VoiceAssistantContext';
import type { VoiceSessionState } from '../../types/voice-assistant';

const STATE_LABELS: Record<VoiceSessionState, string> = {
  idle:       'Ready',
  connecting: 'Connecting...',
  active:     'Session Active',
  ending:     'Ending session...',
  ended:      'Session Ended',
  error:      'Error',
};

const STATE_COLORS: Record<VoiceSessionState, string> = {
  idle:       '#6b7280',   // gray
  connecting: '#f59e0b',   // amber
  active:     '#10b981',   // green
  ending:     '#f59e0b',   // amber
  ended:      '#6b7280',   // gray
  error:      '#ef4444',   // red
};

export function VoiceSessionStatus() {
  const { sessionState, errorMessage } = useVoiceAssistant();

  return (
    <div className="va-status">
      <span
        className="va-status__dot"
        style={{ backgroundColor: STATE_COLORS[sessionState] }}
        aria-hidden="true"
      />
      <span className="va-status__label">
        {STATE_LABELS[sessionState]}
      </span>
      {sessionState === 'error' && errorMessage && (
        <span className="va-status__error" role="alert">
          {errorMessage}
        </span>
      )}
    </div>
  );
}
