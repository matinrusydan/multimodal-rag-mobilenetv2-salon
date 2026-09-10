'use client';

import type React from 'react';
import { useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { AnalyzeResponse, ChatResponse, HairContext } from '@rag-salon/shared-types';

type Message = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ file: string; snippet?: string }>;
};

const WELCOME: Message = {
  id: 0,
  role: 'assistant',
  content:
    'Halo! Saya asisten TIEN SALON. Tanyakan rekomendasi perawatan rambut, atau unggah foto rambutmu untuk analisis otomatis.',
};

function nextMessageId(): number {
  return Date.now() + Math.floor(Math.random() * 1000);
}

export function ConsultChat() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [contextId, setContextId] = useState<string>();
  const [hairContext, setHairContext] = useState<HairContext>();
  const [isSending, setIsSending] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        body: JSON.stringify({ message, hairContext, contextId }),
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

  const handleAnalyze = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || isAnalyzing) {
      return;
    }
    setError('');
    setIsAnalyzing(true);

    try {
      const formData = new FormData();
      formData.append('image', file);
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });
      const body = (await res.json().catch(() => null)) as {
        data?: AnalyzeResponse;
        detail?: string;
        title?: string;
      } | null;

      if (!res.ok || !body?.data) {
        setError(body?.detail ?? body?.title ?? 'Gagal menganalisis foto.');
        return;
      }

      const result = body.data;
      const context: HairContext = {
        hairLength: result.hairLength.label as HairContext['hairLength'],
        hairType: result.hairType.label as HairContext['hairType'],
      };
      setHairContext(context);
      setMessages((current) => [
        ...current,
        {
          id: nextMessageId(),
          role: 'assistant',
          content: `Analisis foto selesai: panjang rambut ${context.hairLength}, jenis rambut ${context.hairType}. Rekomendasi berikutnya akan mempertimbangkan kondisi ini.`,
        },
      ]);
    } catch {
      setError('Terjadi kesalahan jaringan saat menganalisis foto.');
    } finally {
      setIsAnalyzing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <section className="consult-chat">
      <div className="consult-chat__banner">
        <Badge tone="amber">KONSULTASI — Chatbot berbasis RAG + analisis CV</Badge>
      </div>
      {hairContext ? (
        <div className="consult-chat__context">
          <span>Konteks analisis aktif:</span>
          <Badge>{hairContext.hairLength}</Badge>
          <Badge>{hairContext.hairType}</Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setHairContext(undefined)}
            className="consult-chat__clear"
          >
            Hapus
          </Button>
        </div>
      ) : null}
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
            <p>{message.content}</p>
            {message.sources && message.sources.length > 0 ? (
              <ul className="consult-chat__sources">
                {message.sources.map((source) => (
                  <li key={source.file}>
                    Sumber: {source.file}
                    {source.snippet ? ` — ${source.snippet}` : ''}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ))}
        {isSending ? <p className="consult-chat__typing muted-text">Mengetik...</p> : null}
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <div className="consult-chat__composer">
        <input type="file" ref={fileInputRef} accept="image/*" onChange={handleAnalyze} hidden />
        <Button
          variant="outline"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? 'Menganalisis...' : 'Analisis Foto'}
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
    </section>
  );
}
