import type { Message } from "../types";
import { QuoteCard } from "./QuoteCard";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  // Don't render empty assistant bubble (placeholder while loading)
  if (!isUser && !message.content) return null;

  const hasQuote =
    message.content.includes("[QUOTE]") &&
    message.content.includes("[/QUOTE]");

  if (isUser) {
    return (
      <div className="message-row message-row-user">
        <div className="message-bubble message-bubble-user">
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  if (hasQuote) {
    const parts = message.content.split(/\[\/QUOTE\]/);
    const beforeAndQuote = parts[0].split(/\[\*\*QUOTE\*\*\]|\[QUOTE\]/);
    const textBefore = beforeAndQuote[0]?.trim();
    const quoteContent = beforeAndQuote[1]?.trim() || "";
    const textAfter = parts[1]?.trim();

    return (
      <div className="message-row message-row-assistant">
        <div className="message-bubble message-bubble-assistant">
          {textBefore && <p>{textBefore}</p>}
          <QuoteCard content={quoteContent} />
          {textAfter && <div className="message-text">{renderMarkdown(textAfter)}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="message-row message-row-assistant">
      <div className="message-bubble message-bubble-assistant">
        <div className="message-text">{renderMarkdown(message.content)}</div>
      </div>
    </div>
  );
}

function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("- ")) {
      const listItems: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        listItems.push(lines[i].slice(2));
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`}>
          {listItems.map((item, j) => (
            <li key={j} dangerouslySetInnerHTML={{ __html: inlineMarkdown(item) }} />
          ))}
        </ul>
      );
      continue;
    }

    if (line.trim() === "") {
      i++;
      continue;
    }

    elements.push(
      <p key={`p-${i}`} dangerouslySetInnerHTML={{ __html: inlineMarkdown(line) }} />
    );
    i++;
  }

  return elements;
}

function inlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}
