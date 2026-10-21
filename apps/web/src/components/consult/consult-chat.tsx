'use client';

import { useRef, useState } from 'react';

import type { ChatResponse } from '@rag-salon/shared-types';

import { MarkdownLite } from '@/components/consult/markdown-lite';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { cn } from '@/lib/utils';

type Message = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatResponse['sources'];
};

const WELCOME: Message = {
  id: 0,
  role: 'assistant',
  content:
    'Halo! Saya asisten TIEN SALON. Ceritakan kondisi rambutmu atau tanyakan perawatan, layanan, dan harga melalui konsultasi teks. Analisis foto belum tersedia.',
};

function nextMessageId(): number {
  return Date.now() + Math.floor(Math.random() * 1000);
}

export function ConsultChat() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [contextId, setContextId] = useState<string>();
  const [isSending, setIsSending] = useState(false);
  const [photoModalOpen, setPhotoModalOpen] = useState(false);
  const [error, setError] = useState('');
  const photoButtonRef = useRef<HTMLElement | null>(null);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || isSending) {
      return;
    }
    setError('');
    setInput('');
    setMessages((current) => [...current, { id: nextMessageId(), role: 'user', content: message }]);
    setIsSending(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message, contextId }),
      });
      const body = (await res.json().catch(() => null)) as {
        data?: ChatResponse;
        detail?: string;
        title?: string;
      } | null;

      if (!res.ok || !body?.data) {
        setError(body?.detail ?? body?.title ?? 'Gagal mendapatkan balasan.');
        setMessages((current) => [...current.slice(0, -1)]);
        return;
      }

      const data = body.data;
      setContextId(data.contextId);
      setMessages((current) => [
        ...current,
        { id: nextMessageId(), role: 'assistant', content: data.reply, sources: data.sources },
      ]);
    } catch {
      setError('Terjadi kesalahan jaringan. Silakan coba lagi.');
      setMessages((current) => [...current.slice(0, -1)]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <section className="consult-chat">
      <div className="consult-chat__banner">
        <Badge tone="amber">KONSULTASI — Chatbot teks berbasis RAG</Badge>
      </div>
      <div className="consult-chat__messages" aria-live="polite">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'consult-chat__bubble',
              message.role === 'user'
                ? 'consult-chat__bubble--user'
                : 'consult-chat__bubble--assistant',
            )}
          >
            <MarkdownLite content={message.content} />
            {message.sources && message.sources.length > 0 ? (
              <div className="consult-chat__sources-block">
                <span className="consult-chat__sources-label">Sumber</span>
                <ul className="consult-chat__sources">
                  {message.sources.map((source, idx) => {
                    const isWeb = source.file.startsWith('web:');
                    const href =
                      source.url ||
                      (isWeb
                        ? `https://www.alodokter.com/${source.file.replace(/^web:/, '')}`
                        : undefined);
                    const title =
                      source.title ||
                      source.section ||
                      (isWeb ? 'Artikel web' : source.file.replace(/\.md$/, ''));
                    const label = source.citation_number
                      ? `[${source.citation_number}] ${title}`
                      : title;
                    return (
                      <li key={`${source.file}-${idx}`}>
                        {href && /^https?:\/\//i.test(href) ? (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="consult-chat__source-link"
                          >
                            {label}
                          </a>
                        ) : (
                          <span className="consult-chat__source-kb">{label}</span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}
          </div>
        ))}
        {isSending ? <p className="consult-chat__typing muted-text">Mengetik...</p> : null}
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <div className="consult-chat__composer">
        <Button
          variant="outline"
          size="sm"
          onClick={(event) => {
            photoButtonRef.current = event.currentTarget;
            setPhotoModalOpen(true);
          }}
        >
          Analisis Foto
        </Button>
        <input
          type="text"
          value={input}
          placeholder="Tanya rekomendasi perawatan rambut..."
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void handleSend();
            }
          }}
        />
        <Button size="sm" onClick={handleSend} disabled={isSending || !input.trim()}>
          Kirim
        </Button>
      </div>
      <Modal
        open={photoModalOpen}
        onOpenChange={setPhotoModalOpen}
        title="Fitur belum tersedia"
        description="Analisis foto belum tersedia."
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          photoButtonRef.current?.focus();
        }}
      >
        <p>Silakan ceritakan kondisi rambutmu melalui konsultasi teks.</p>
      </Modal>
    </section>
  );
}
