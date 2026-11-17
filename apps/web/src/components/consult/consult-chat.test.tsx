import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ConsultChat } from './consult-chat';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  // Keep the existing timestamp/random message IDs deterministic in UI regressions.
  let now = 1_700_000_000_000;
  vi.spyOn(Date, 'now').mockImplementation(() => ++now);
  vi.spyOn(Math, 'random').mockReturnValue(0);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('ConsultChat', () => {
  it('menyediakan input file tersembunyi dan tombol trigger Analisis Foto', async () => {
    const { container } = render(<ConsultChat />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const photoButton = screen.getByRole('button', { name: 'Analisis Foto' });

    expect(fileInput).not.toBeNull();
    expect(fileInput.accept).toBe('image/jpeg,image/png,image/webp');
    expect(photoButton).toBeInTheDocument();
  });

  it('melakukan analisis foto, menampilkan badge konteks dan atribut multi-atribut', async () => {
    const analyzeData = {
      hairType: { label: 'lurus', confidence: 0.99 },
      hairLength: { label: 'menengah', confidence: 0.85 },
      hairVolume: { label: 'sedang', confidence: 0.8 },
      tiedHair: { tied: false, style: 'loose', confidence: 0.9 },
      hairFeatures: {
        color: 'cokelat',
        texture: 'halus',
        health: 'tidak-diketahui',
        riskSigns: { bleach: false, dry: true },
      },
      status: 'ok',
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, data: analyzeData }),
    });

    const { container } = render(<ConsultChat />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(['fake-hair-image'], 'photo.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('lurus')).toBeInTheDocument();
      expect(screen.getByText('menengah')).toBeInTheDocument();
      expect(screen.getByText('volume: sedang')).toBeInTheDocument();
      expect(screen.getByText('cokelat')).toBeInTheDocument();
      expect(screen.getByText('indikasi kering')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Analisis foto selesai: jenis rambut lurus, panjang menengah/i),
    ).toBeInTheDocument();
  });

  it('menangani hasil klasifikasi 3-kelas keriting dengan atribut volume dan tatanan terikat', async () => {
    const analyzeData = {
      hairType: { label: 'keriting', confidence: 0.98 },
      hairLength: { label: 'panjang', confidence: 0.88 },
      hairVolume: { label: 'tebal', confidence: 0.82 },
      tiedHair: { tied: true, style: 'ponytail', confidence: 0.95 },
      hairFeatures: {
        color: 'hitam',
        texture: 'kasar',
        health: 'tidak-diketahui',
        riskSigns: { bleach: false, dry: false },
      },
      status: 'ok',
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, data: analyzeData }),
    });

    const { container } = render(<ConsultChat />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(['fake-curly-hair'], 'curly.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('keriting')).toBeInTheDocument();
      expect(screen.getByText('panjang')).toBeInTheDocument();
      expect(screen.getByText('volume: tebal')).toBeInTheDocument();
      expect(screen.getByText('ponytail')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Analisis foto selesai: jenis rambut keriting, panjang panjang/i),
    ).toBeInTheDocument();
  });

  it('mempertahankan chat teks, contextId, markdown, dan sumber', async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: {
            reply: 'Gunakan **perawatan lembut**.',
            contextId: 'evidence-1',
            sources: [
              { file: 'care.md', title: 'Panduan salon', citation_number: 1 },
              {
                file: 'web:perawatan',
                title: 'Artikel perawatan',
                url: 'https://example.com/care',
              },
            ],
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { reply: 'Silakan tanyakan layanan.', contextId: 'evidence-2' },
        }),
      });
    render(<ConsultChat />);
    const input = screen.getByRole('textbox');
    await user.type(input, 'Rambut saya kering{Enter}');
    expect(await screen.findByText('perawatan lembut')).toHaveProperty('tagName', 'STRONG');
    expect(screen.getByText('[1] Panduan salon')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Artikel perawatan' })).toHaveAttribute(
      'href',
      'https://example.com/care',
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ message: 'Rambut saya kering' });

    await user.type(input, 'Apa layanannya?');
    await user.click(screen.getByRole('button', { name: 'Kirim' }));
    expect(await screen.findByText('Silakan tanyakan layanan.')).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      message: 'Apa layanannya?',
      contextId: 'evidence-1',
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/chat', '/api/chat']);
  });

  it.each([
    {
      response: { ok: false, json: async () => ({ detail: 'Layanan sedang sibuk.' }) },
      error: 'Layanan sedang sibuk.',
    },
    {
      response: { ok: false, json: async () => ({ title: 'Waktu tunggu habis' }) },
      error: 'Waktu tunggu habis',
    },
    { response: { ok: true, json: async () => null }, error: 'Gagal mendapatkan balasan.' },
  ])('mempertahankan pesan kesalahan $error', async ({ response, error }) => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValueOnce(response);
    render(<ConsultChat />);
    await user.type(screen.getByRole('textbox'), 'Pertanyaan gagal{Enter}');
    expect(await screen.findByText(error)).toBeInTheDocument();
    expect(screen.queryByText('Pertanyaan gagal')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeEnabled();
  });

  it('mempertahankan penanganan kegagalan jaringan', async () => {
    const user = userEvent.setup();
    fetchMock.mockRejectedValueOnce(new TypeError('offline'));
    render(<ConsultChat />);
    await user.type(screen.getByRole('textbox'), 'Pertanyaan gagal{Enter}');
    expect(
      await screen.findByText('Terjadi kesalahan jaringan. Silakan coba lagi.'),
    ).toBeInTheDocument();
    expect(screen.queryByText('Pertanyaan gagal')).not.toBeInTheDocument();
  });
});
