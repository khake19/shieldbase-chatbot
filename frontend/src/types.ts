export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface ChatResponseData {
  response: string;
  session_id: string;
  current_mode: string;
  insurance_type: string | null;
  quote_step: string | null;
  quote_data: Record<string, unknown>;
}

export interface SSEEvent {
  type: "session" | "start" | "chunk" | "end" | "error" | "stage";
  content?: string;
  session_id?: string;
  current_mode?: string;
  insurance_type?: string | null;
  quote_step?: string | null;
  quote_data?: Record<string, unknown>;
}
