import { useEffect, useRef } from "react";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";
import { LoadingIndicator } from "./LoadingIndicator";

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  processingStage?: string | null;
}

export function ChatWindow({ messages, isLoading, processingStage }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      {messages.length === 0 && (
        <div className="welcome-message">
          <div className="welcome-icon">
            <svg
              width="48"
              height="48"
              viewBox="0 0 64 64"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M32 4L8 16v16c0 14.4 10.24 27.84 24 32 13.76-4.16 24-17.6 24-32V16L32 4z"
                fill="#1e3a5f"
                stroke="#2563eb"
                strokeWidth="2"
              />
              <path
                d="M32 12L14 20v12c0 10.8 7.68 20.88 18 24 10.32-3.12 18-13.2 18-24V20L32 12z"
                fill="#2563eb"
                opacity="0.3"
              />
              <path d="M28 30l-4-4-2 2 6 6 12-12-2-2-10 10z" fill="white" />
            </svg>
          </div>
          <h2>Welcome to ShieldBase Insurance</h2>
          <p>
            I'm your insurance assistant. I can help you with:
          </p>
          <div className="welcome-options">
            <div className="welcome-option">
              <strong>Get a Quote</strong>
              <span>Auto, Home, or Life insurance quotes in minutes</span>
            </div>
            <div className="welcome-option">
              <strong>Ask Questions</strong>
              <span>Coverage details, claims, pricing, and more</span>
            </div>
          </div>
          <p className="welcome-hint">Type a message below to get started!</p>
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isLoading && <LoadingIndicator stage={processingStage} />}

      <div ref={bottomRef} />
    </div>
  );
}
