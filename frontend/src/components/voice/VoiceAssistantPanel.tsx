// frontend/src/components/voice/VoiceAssistantPanel.tsx
//
// The main panel that composes all voice UI components.
// This is the only component that needs to be imported by the page.
// It also renders RoomAudioRenderer which plays the agent's voice through speakers.

import React from 'react';
import './voice-assistant.css';
import { RoomContext, RoomAudioRenderer } from '@livekit/components-react';
import { room } from '../../contexts/VoiceAssistantContext';
import { VoiceSessionStatus }    from './VoiceSessionStatus';
import { AgentSpeakingIndicator } from './AgentSpeakingIndicator';
import { VoiceSessionControls }   from './VoiceSessionControls';
import { ConversationTranscript } from './ConversationTranscript';
import { useVoiceAssistant }      from '../../contexts/VoiceAssistantContext';

export function VoiceAssistantPanel() {
  const { sessionState } = useVoiceAssistant();
  const isSessionActive = sessionState === 'active' || sessionState === 'ending' || sessionState === 'ended';

  return (
    // RoomContext gives @livekit/components-react hooks access to our room instance.
    // This is required for RoomAudioRenderer to work. We use our manually created room
    // instance (not a wrapper room component) because we manage connection state ourselves
    // in VoiceAssistantContext.
    <RoomContext.Provider value={room}>
      <div className="va-panel" role="region" aria-label="Voice Assistant">
        <div className="va-panel__header">
          <h3 className="va-panel__title">AI Job Posting Assistant</h3>
          <VoiceSessionStatus />
        </div>

        <div className="va-panel__body">
          <AgentSpeakingIndicator />

          {isSessionActive && (
            <ConversationTranscript />
          )}
        </div>

        <div className="va-panel__footer">
          <VoiceSessionControls />
        </div>

        {/*
          RoomAudioRenderer MUST be rendered inside the room context provider.
          It automatically subscribes to all remote audio tracks and plays them
          through the browser's audio output. Without this, you will not hear
          the agent speaking even though the audio track is subscribed.
          It renders no visible DOM element.
        */}
        <RoomAudioRenderer />
      </div>
    </RoomContext.Provider>
  );
}
