/**
 * Markdown chunking for the knowledge base.
 * Chunk size 500-1000 estimated tokens with 100-token overlap (chars/4 heuristic).
 * Splits follow markdown sections (##) and avoids cutting mid-sentence.
 */

export interface RAGChunk {
  text: string;
  section: string;
}

export interface ChunkerOptions {
  /** Upper bound of estimated tokens per chunk. */
  maxTokens?: number;
  /** Estimated tokens carried over between consecutive chunks. */
  overlapTokens?: number;
  /** Estimated tokens a chunk should reach before being flushed. */
  minTokens?: number;
}

const DEFAULT_OPTIONS: Required<ChunkerOptions> = {
  maxTokens: 1000,
  overlapTokens: 100,
  minTokens: 500,
};

/** Approximate tokens via ~4 chars per token (enough for chunk bounds). */
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

/** Split markdown into level-2 (##) sections. */
export function splitSections(markdown: string): { header: string; body: string }[] {
  const sections: { header: string; body: string[] }[] = [];
  for (const line of markdown.split('\n')) {
    const m = /^#{2,}\s+(.*)$/.exec(line);
    if (m) {
      sections.push({ header: m[1].trim(), body: [] });
    } else if (sections.length > 0) {
      const last = sections[sections.length - 1];
      if (last) last.body.push(line);
    }
  }
  return sections.map((s) => ({ header: s.header, body: s.body.join('\n').trim() }));
}

/** Split text into sentence-ish units, never cutting mid-sentence. */
export function splitSentences(text: string): string[] {
  return text
    .replace(/\r\n/g, '\n')
    .split(/\n+/) // keep bullet/list lines intact
    .flatMap((line) => line.split(/(?<=[.!?])\s+/))
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Chunk a whole markdown document.
 * Each chunk stays within maxTokens and carries ~overlapTokens from the
 * previous chunk. Sections are kept separate (overlap resets between them).
 */
export function chunkMarkdown(markdown: string, options: ChunkerOptions = {}): RAGChunk[] {
  const { maxTokens, overlapTokens, minTokens } = { ...DEFAULT_OPTIONS, ...options };
  const chunks: RAGChunk[] = [];

  for (const section of splitSections(markdown)) {
    if (!section.header.trim()) continue;
    const sentences = splitSentences(section.body);
    if (sentences.length === 0) continue;

    let current: string[] = [];
    let overlapParts: string[] = [];

    const flush = () => {
      const text = [...overlapParts, ...current].join(' ').trim();
      if (!text) return;
      const full = text.length;
      chunks.push({ text, section: section.header });
      overlapParts = [];
      let carry = '';
      for (let i = full - 1; i >= 0 && estimateTokens(carry) < overlapTokens; i--) {
        carry = `${text[i] ?? ''}${carry}`;
      }
      overlapParts = carry !== '' ? carry.trim().split(' ').filter(Boolean) : [];
      current = [];
    };

    for (const sentence of sentences) {
      const candidate = [...overlapParts, ...current, sentence].join(' ');
      if (
        current.length > 0 &&
        estimateTokens(candidate) > maxTokens &&
        estimateTokens([...overlapParts, ...current].join(' ')) >= minTokens
      ) {
        flush();
      }
      current.push(sentence);
      if (estimateTokens([...overlapParts, ...current].join(' ')) >= maxTokens) {
        flush();
      }
    }
    flush();
  }

  // Fallback for markdown without any ## section.
  if (chunks.length === 0) {
    const sentences = splitSentences(markdown);
    let buff: string[] = [];
    for (const sentence of sentences) {
      buff.push(sentence);
      if (estimateTokens(buff.join(' ')) >= minTokens) {
        chunks.push({ text: buff.join(' '), section: 'Dokumen' });
        buff = [];
      }
    }
    if (buff.length) chunks.push({ text: buff.join(' '), section: 'Dokumen' });
  }

  return chunks;
}
