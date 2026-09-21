import type { Metadata } from 'next';

import { KnowledgeManager } from '@/components/admin/knowledge-manager';

export const metadata: Metadata = {
  title: 'Dokumen RAG',
};

export default function AdminKnowledgePage() {
  return <KnowledgeManager />;
}
