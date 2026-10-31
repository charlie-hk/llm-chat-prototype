// Streams a chat reply from the backend.
// Calls onToken for each piece of text as it arrives.
// Returns when the stream is done; throws on an error event or network failure.
export async function streamChat(messages, { onToken, signal }) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Server responded ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const event = JSON.parse(line.slice(5).trim());

      if (event.type === "token") onToken(event.value);
      else if (event.type === "error") throw new Error(event.message);
      else if (event.type === "done") return;
    }
  }
}

export async function fetchConfig() {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error("config failed");
  return res.json();
}
