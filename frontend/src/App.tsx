import { ChatWindow } from "./components/ChatWindow";
import { ChatInput } from "./components/ChatInput";
import { useChat } from "./hooks/useChat";
import "./styles/chat.css";

function App() {
  const { messages, isLoading, sendMessage, clearChat } = useChat();

  return (
    <div className="app">
      <header className="header">
        <img
          src="/shieldbase-logo.svg"
          alt="ShieldBase"
          className="header-logo"
        />
        <div>
          <span className="header-title">ShieldBase</span>
          <span className="header-subtitle">Insurance Assistant</span>
        </div>
        <div className="header-actions">
          <button className="clear-button" onClick={clearChat}>
            New Chat
          </button>
        </div>
      </header>

      <ChatWindow messages={messages} isLoading={isLoading} />

      <div className="chat-input-container">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}

export default App;
