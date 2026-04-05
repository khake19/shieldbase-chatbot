import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus on mount and after sending (when disabled goes from true → false)
  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <textarea
        ref={inputRef}
        className="chat-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about our insurance plans or get a quote..."
        disabled={disabled}
        rows={1}
      />
      <button
        type="submit"
        className="send-button"
        disabled={disabled || !input.trim()}
        aria-label="Send message"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </form>
  );
}
