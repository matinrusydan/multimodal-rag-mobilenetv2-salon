import { cleanup, render, screen, waitFor } from '@testing-library/react';
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
  it('membuka modal tanpa unggahan dan mengembalikan fokus setelah ditutup', async () => {
    const user = userEvent.setup();
    const { container } = render(<ConsultChat />);
    const photoButton = screen.getByRole('button', { name: 'Analisis Foto' });

    expect(container.querySelector('input[type="file"]')).toBeNull();
    await user.click(photoButton);
    expect(screen.getByRole('dialog', { name: 'Fitur belum tersedia' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Tutup' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(photoButton).toHaveFocus();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(['{Enter}', ' '])('mendukung keyboard %s dan Escape tanpa analisis', async (key) => {
    const user = userEvent.setup();
    render(<ConsultChat />);
    const photoButton = screen.getByRole('button', { name: 'Analisis Foto' });
    await user.tab();
    expect(photoButton).toHaveFocus();
    await user.keyboard(key);
    expect(screen.getByRole('dialog', { name: 'Fitur belum tersedia' })).toBeInTheDocument();
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(photoButton).toHaveFocus();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('mempertahankan chat teks, contextId, markdown, dan sumber setelah modal ditutup', async () => {
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
    await user.click(screen.getByRole('button', { name: 'Analisis Foto' }));
    await user.keyboard('{Escape}');
    expect(input).toHaveValue('Apa layanannya?');
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
