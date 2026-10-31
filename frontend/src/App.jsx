import { useEffect, useRef, useState } from "react";
import { streamChat, fetchConfig } from "./api.js";

const WELCOME = { role: "assistant", content: "Hi. Ask me anything to get started." };

export default function App() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    fetchConfig()
      .then((c) => setInfo(c.model ? `${c.provider} · ${c.model}` : c.provider))
      .catch(() => setInfo(""));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    setError(null);
    setInput("");
    setBusy(true);

    // Everything except the welcome line is the real context sent to the model.
    const history = messages.filter((m) => m !== WELCOME);
    const next = [...history, { role: "user", content: text }];
    setMessages([...messages, { role: "user", content: text }, { role: "assistant", content: "" }]);

    try {
      await streamChat(next, {
        onToken: (t) =>
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = {
              role: "assistant",
              content: copy[copy.length - 1].content + t,
            };
            return copy;
          }),
      });
    } catch (e) {
      setError(e.message || "Something went wrong.");
      setMessages((prev) => prev.slice(0, -1)); // drop the empty assistant bubble
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setMessages([WELCOME]);
    setError(null);
    setInput("");
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="app">
      <header className="bar">
        <div className="title">
          LLM Chat Prototype
          {info && <span className="badge">{info}</span>}
        </div>
        <button className="ghost" onClick={reset} disabled={busy}>
          New conversation
        </button>
      </header>

      <main className="thread" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`row ${m.role}`}>
            <div className="bubble">
              {m.content || <span className="cursor">▍</span>}
            </div>
          </div>
        ))}
        {error && <div className="row error"><div className="bubble">{error}</div></div>}
      </main>

      <footer className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type a message, then Enter"
          rows={1}
        />
        <button onClick={send} disabled={busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </footer>
    </div>
  );
}
