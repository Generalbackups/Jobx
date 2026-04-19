// frontend/src/components/voice/ConversationTranscript.tsx
//
// Scrollable conversation feed. Shows agent messages on the left,
// user messages on the right. Auto-scrolls to the latest message.
// Partial (non-final) transcriptions are shown in italic until finalized.

import React, { useEffect, useRef } from 'react';
import { useVoiceAssistant } from '../../contexts/VoiceAssistantContext';

export function ConversationTranscript() {
  const { transcript, sessionState } = useVoiceAssistant();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever transcript updates
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  const isActive = sessionState === 'active' || sessionState === 'ending';

  if (transcript.length === 0) {
    return (
      <div className="va-transcript va-transcript--empty">
        {isActive
          ? 'Conversation will appear here...'
          : 'Start a session to begin the conversation.'}
      </div>
    );
  }

  return (
    <div className="va-transcript" role="log" aria-live="polite" aria-label="Conversation transcript">
      {transcript.map((entry) => (
        <div
          key={entry.id}
          className={[
            'va-transcript__entry',
            entry.role === 'agent'
              ? 'va-transcript__entry--agent'
              : 'va-transcript__entry--user',
          ].join(' ')}
        >
          <span className="va-transcript__role">
            {entry.role === 'agent' ? 'Assistant' : 'You'}
          </span>
          <p
            className={[
              'va-transcript__text',
              !entry.isFinal ? 'va-transcript__text--partial' : '',
            ].filter(Boolean).join(' ')}
          >
            {entry.content}
          </p>
          <span className="va-transcript__time" aria-hidden="true">
            {new Date(entry.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      ))}
      <div ref={bottomRef} aria-hidden="true" />
    </div>
  );
}
