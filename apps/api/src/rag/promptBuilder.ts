import type { HairContext, HairFeatures } from '@rag-salon/shared-types';
import type { ChatCompletionMessageParam } from 'openai/resources/chat/completions';
import type { RetrievedDoc } from './retriever';

export type { HairFeatures };

export interface PromptInput {
  query: string;
  docs: RetrievedDoc[];
  hairContext?: HairContext;
  hairFeatures?: HairFeatures;
}

/** Marker sumber untuk membantu LLM menyebutkan referensi. */
function formatDocs(docs: RetrievedDoc[]): string {
  return docs
    .map((d, i) => {
      const src = d.section ? `${d.file}#${d.section}` : d.file;
      const snippet = d.snippet?.slice(0, 500) ?? '';
      return `[${i + 1}] ${src}\n${snippet}`.trim();
    })
    .join('\n\n---\n\n');
}

/**
 * Build prompt chat completions untuk konsultasi rambut.
 * Urutan: system -> user(content: konteks CV + retrieved docs + query).
 * Tidak ada yang boleh menyuntik system prompt baru dari input user.
 */
export function buildPrompt(input: PromptInput): ChatCompletionMessageParam[] {
  const system: ChatCompletionMessageParam = {
    role: 'system',
    content:
      'Kamu adalah asisten konsultasi rambut "TIEN SALON", sebuah salon rambut di Indonesia. ' +
      'Jawab selalu dalam Bahasa Indonesia yang ramah, jelas, dan ringkas. ' +
      'Gunakan hanya informasi dari dokumen knowledge base yang diberikan. ' +
      'Jika informasi tidak tersedia di dokumen, katakan bahwa Anda perlu konfirmasi langsung ke salon. ' +
      'Sebutkan sumber (nama file dan bagian) hanya bila relevan. ' +
      'Jangan mengarang nomor telepon, alamat, harga, atau kebijakan yang tidak ada di dokumen.',
  };

  const parts: string[] = [];

  if (input.hairContext) {
    parts.push(
      `KONTEKS RAMBUT PELANGGAN (hasil analisis foto komputer): panjang=${input.hairContext.hairLength}; jenis=${input.hairContext.hairType}.`,
    );
  }

  if (input.hairFeatures) {
    const { color, texture, health, riskSigns } = input.hairFeatures;
    const featBits = [
      color && `warna=${color}`,
      texture && `tekstur=${texture}`,
      health && `kondisi=${health}`,
    ]
      .filter(Boolean)
      .join('; ');
    if (featBits) parts.push(`FITUR RAMBUT (analisis): ${featBits}.`);
    if (riskSigns?.bleach || riskSigns?.dry) {
      parts.push(
        'PERINGATAN: analisis menunjukkan kemungkinan rambut mengalami bleaching/pewarnaan keras ' +
          'atau kondisi kering. Bila pelanggan menanyakan smoothing/rebonding, ' +
          'berikan disclaimer bahwa hasil bisa bervariasi, risiko kerusakan lebih tinggi, ' +
          'serta sarankan konsultasi & uji keamanan langsung dengan stylist TIEN SALON.',
      );
    }
  }

  parts.push(
    'INSTRUKSI FORMAT: jawab langsung tanpa sapaan berulang, gunakan poin bila perlu, maksimal ~200 kata.',
  );

  const docs = formatDocs(input.docs);
  parts.push(
    docs
      ? `DOKUMEN KNOWLEDGE BASE (sumber jawaban):\n\n${docs}`
      : 'TIDAK ADA DOKUMEN yang terambil. Bila tidak ada dokumen, jawab seadanya dan sarankan menghubungi salon.',
  );

  parts.push(`PERTANYAAN PELANGGAN: ${input.query}`);

  const user: ChatCompletionMessageParam = {
    role: 'user',
    content: parts.join('\n\n'),
  };

  return [system, user];
}
