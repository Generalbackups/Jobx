// frontend/src/components/voice/AgentSpeakingIndicator.tsx
//
// Animated orb that pulses when the AI agent is speaking.
// Uses CSS keyframe animation defined in voice-assistant.css.

import React from 'react';
import { useVoiceAssistant } from '../../contexts/VoiceAssistantContext';

export function AgentSpeakingIndicator() {
  const { isAgentSpeaking, sessionState } = useVoiceAssistant();
  const isActive = sessionState === 'active' || sessionState === 'ending';

  return (
    <div className="va-agent-orb-wrapper" aria-label="AI assistant speaking indicator">
      <div
        className={[
          'va-agent-orb',
          isActive && isAgentSpeaking ? 'va-agent-orb--speaking' : '',
          isActive && !isAgentSpeaking ? 'va-agent-orb--listening' : '',
        ].filter(Boolean).join(' ')}
      >
        {/* Inner circles for the pulse animation layers */}
        <div className="va-agent-orb__core" />
        <div className="va-agent-orb__ring va-agent-orb__ring--1" />
        <div className="va-agent-orb__ring va-agent-orb__ring--2" />
      </div>
      <p className="va-agent-orb__label">
        {!isActive
          ? 'Assistant'
          : isAgentSpeaking
          ? 'Speaking...'
          : 'Listening'}
      </p>
    </div>
  );
}
