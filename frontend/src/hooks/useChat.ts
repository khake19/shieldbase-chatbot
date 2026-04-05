import { useState, useCallback, useRef } from "react";
import type { Message, SSEEvent } from "../types";

const API_BASE = "http://localhost:8000";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [processingStage, setProcessingStage] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setProcessingStage(null);

    const assistantId = crypto.randomUUID();

    try {
      const params = new URLSearchParams({ message: content });
      if (sessionIdRef.current) {
        params.set("session_id", sessionIdRef.current);
      }

      const response = await fetch(
        `${API_BASE}/chat/stream?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let fullContent = "";
      let buffer = "";

      // Add empty assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date(),
        },
      ]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last (possibly incomplete) line in the buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event: SSEEvent = JSON.parse(jsonStr);

            if (event.type === "session" && event.session_id) {
              sessionIdRef.current = event.session_id;
            } else if (event.type === "stage" && event.content) {
              setProcessingStage(event.content);
            } else if (event.type === "chunk" && event.content) {
              setProcessingStage(null);
              fullContent += event.content;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: fullContent }
                    : msg
                )
              );
            } else if (event.type === "error") {
              fullContent =
                event.content || "Sorry, something went wrong. Please try again.";
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: fullContent }
                    : msg
                )
              );
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                content:
                  "Sorry, I couldn't connect to the server. Please make sure the backend is running.",
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      setProcessingStage(null);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = null;
  }, []);

  return { messages, isLoading, processingStage, sendMessage, clearChat };
}
