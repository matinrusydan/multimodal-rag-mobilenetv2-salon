import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MarkdownLite } from './markdown-lite';

describe('MarkdownLite', () => {
  it('merender **bold** sebagai <strong>, bukan simbol bintang', () => {
    render(<MarkdownLite content="Ini **tebal** biasa." />);
    const strong = screen.getByText('tebal');
    expect(strong.tagName).toBe('STRONG');
    expect(screen.queryByText(/\*\*/)).toBeNull();
  });

  it('merender *italic* sebagai <em>', () => {
    render(<MarkdownLite content="Fase *telogen* istirahat." />);
    const em = screen.getByText('telogen');
    expect(em.tagName).toBe('EM');
  });

  it('merender bullet menjadi daftar <li>', () => {
    render(<MarkdownLite content={'Penyebab:\n• Stres\n• Gizi kurang\n- Hormon'} />);
    expect(screen.getByText('Stres').tagName).toBe('LI');
    expect(screen.getByText('Gizi kurang').tagName).toBe('LI');
    expect(screen.getByText('Hormon').tagName).toBe('LI');
    expect(screen.getByRole('list')).toBeTruthy();
  });

  it('menggabungkan bold di dalam bullet', () => {
    render(<MarkdownLite content="• **Faktor Tubuh:** stres berat" />);
    const strong = screen.getByText('Faktor Tubuh:');
    expect(strong.tagName).toBe('STRONG');
  });

  it('memisahkan paragraf pada baris kosong', () => {
    render(<MarkdownLite content={'Paragraf satu.\n\nParagraf dua.'} />);
    expect(screen.getByText('Paragraf satu.').tagName).toBe('P');
    expect(screen.getByText('Paragraf dua.').tagName).toBe('P');
  });

  it('merender `code` inline', () => {
    render(<MarkdownLite content="Gunakan `dry shampoo` bila perlu." />);
    expect(screen.getByText('dry shampoo').tagName).toBe('CODE');
  });
});
