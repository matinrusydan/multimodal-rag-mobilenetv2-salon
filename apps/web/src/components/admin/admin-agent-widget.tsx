'use client';

import { useEffect, useRef, useState } from 'react';

import { MarkdownLite } from '@/components/consult/markdown-lite';
import { cn } from '@/lib/utils';

type Message = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  tools?: string[];
};

const WELCOME: Message = {
  id: 0,
  role: 'assistant',
  content:
    'Halo! Saya agent admin salon. Tanyakan misalnya:\n- "Layanan apa saja yang tersedia?"\n- "Berapa pemasukan saat ini?"\n- "Ada berapa reservasi minggu ini?"',
};

function nextId(): number {
  return Date.now() + Math.floor(Math.random() * 1000);
}

export function AdminAgentWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, open]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || isSending) {
      return;
    }
    setError('');
    setInput('');
    setMessages((current) => [...current, { id: nextId(), role: 'user', content: message }]);
    setIsSending(true);

    try {
      const history = messages
        .filter((m) => m.id !== WELCOME.id)
        .slice(-8)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await fetch('/api/admin/agent', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message, history }),
      });
      const body = (await res.json().catch(() => null)) as {
        data?: { reply: string; toolTrace?: Array<{ tool: string }> };
        detail?: string;
        title?: string;
      } | null;

      if (!res.ok || !body?.data) {
        setError(body?.detail ?? body?.title ?? 'Gagal mendapatkan balasan.');
        setMessages((current) => [...current.slice(0, -1)]);
        return;
      }

      const data = body.data;
      const tools = (data.toolTrace ?? []).map((t) => t.tool);
      setMessages((current) => [
        ...current,
        { id: nextId(), role: 'assistant', content: data.reply, tools },
      ]);
    } catch {
      setError('Terjadi kesalahan jaringan. Silakan coba lagi.');
      setMessages((current) => [...current.slice(0, -1)]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="admin-agent">
      {open ? (
        <div className="admin-agent__panel" role="dialog" aria-label="Agent Admin">
          <header className="admin-agent__header">
            <div>
              <strong>Agent Admin</strong>
              <span className="admin-agent__subtitle">RAG + data live</span>
            </div>
            <button
              type="button"
              className="admin-agent__close"
              onClick={() => setOpen(false)}
              aria-label="Tutup"
            >
              ×
            </button>
          </header>

          <div className="admin-agent__messages" ref={listRef} aria-live="polite">
            {messages.map((m) => (
              <div
                key={m.id}
                className={cn(
                  'admin-agent__bubble',
                  m.role === 'user' ? 'admin-agent__bubble--user' : 'admin-agent__bubble--assistant',
                )}
              >
                <MarkdownLite content={m.content} />
                {m.tools && m.tools.length > 0 ? (
                  <div className="admin-agent__tools">data: {m.tools.join(', ')}</div>
                ) : null}
              </div>
            ))}
            {isSending ? <p className="admin-agent__typing">Mengetik...</p> : null}
          </div>

          {error ? <p className="admin-agent__error">{error}</p> : null}

          <div className="admin-agent__composer">
            <input
              type="text"
              value={input}
              placeholder="Tanya layanan / pemasukan / reservasi..."
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
            />
            <button type="button" onClick={handleSend} disabled={isSending || !input.trim()}>
              Kirim
            </button>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        className="admin-agent__fab"
        onClick={() => setOpen((v) => !v)}
        aria-label="Buka agent admin"
        title="Agent Admin"
      >
        {open ? '×' : '💬'}
      </button>
    </div>
  );
}
