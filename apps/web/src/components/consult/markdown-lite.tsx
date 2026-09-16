'use client';

import type React from 'react';

/**
 * Renderer markdown minimalis untuk balasan chatbot.
 * Mendukung: **bold**, *italic*, `code`, bullet (•/-/*), dan paragraf.
 * Aman: tidak memakai dangerouslySetInnerHTML.
 */

const INLINE_RE = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`)/g;

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  INLINE_RE.lastIndex = 0;
  // eslint-disable-next-line no-cond-assign
  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-${i++}`;
    if (token.startsWith('**') && token.endsWith('**')) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*')) {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith('`') && token.endsWith('`')) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

const BULLET_RE = /^\s*[•*-]\s+(.*)$/;

export function MarkdownLite({ content }: { content: string }) {
  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let listBuffer: string[] = [];
  let key = 0;

  const flushList = () => {
    if (listBuffer.length === 0) {
      return;
    }
    blocks.push(
      <ul key={`ul-${key++}`} className="consult-chat__md-list">
        {listBuffer.map((item, idx) => (
          <li key={`li-${key}-${idx}`}>{renderInline(item, `li-${key}-${idx}`)}</li>
        ))}
      </ul>,
    );
    listBuffer = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.replace(/\s+$/, '');
    const bullet = line.match(BULLET_RE);
    if (bullet && bullet[1] !== undefined) {
      listBuffer.push(bullet[1]);
      continue;
    }
    flushList();
    if (line.trim() === '') {
      continue;
    }
    blocks.push(
      <p key={`p-${key++}`} className="consult-chat__md-p">
        {renderInline(line, `p-${key}`)}
      </p>,
    );
  }
  flushList();

  return <div className="consult-chat__content">{blocks}</div>;
}
