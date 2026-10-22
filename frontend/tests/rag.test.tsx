import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { SourceSearch } from '../src/materials/SourceSearch';
import { ApiError } from '../src/api';

const call = vi.fn();
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call }) }));
const mid = '11111111-1111-4111-8111-111111111111';
const ready = { state: 'ready', chunks: 2, indexed: 2, model_available: true };
function search() {
  fireEvent.change(screen.getByLabelText('Topic or question'), { target: { value: 'normalization' } });
  fireEvent.submit(screen.getByRole('form', { name: 'Search source passages' }));
}
describe('local source retrieval', () => {
  it('shows missing local model and disables indexing without cloud fallback', async () => {
    call.mockResolvedValue({ ...ready, state: 'not_indexed', indexed: 0, model_available: false });
    render(<SourceSearch materialId={mid} onPage={vi.fn()} />);
    expect(await screen.findByText(/local search model needs setup/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Prepare for search' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Find passages' })).toBeDisabled();
  });
  it('prepares a selected material then enables retrieval', async () => {
    call.mockImplementation(async (path: string) => path.endsWith('/index') ? ready : { ...ready, state: 'partial', indexed: 1 });
    render(<SourceSearch materialId={mid} onPage={vi.fn()} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Prepare for search' }));
    expect(await screen.findByText('Ready to search')).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith(`/rag/materials/${mid}/index`, expect.objectContaining({ method: 'POST' }));
  });
  it('keeps source text inert, preserves citations and opens the original page', async () => {
    const page = vi.fn();
    call.mockImplementation(async (path: string) => path.endsWith('/search') ? { status: 'sources_found', sources: [{ citation: 'S1', chunk_id: 'chunk', title: 'Source', page_start: 2, page_end: 2, excerpt: '<script>not executed</script>', similarity: 0.75, clipped: true }] } : ready);
    render(<SourceSearch materialId={mid} onPage={page} />); await screen.findByText('Ready to search'); search();
    expect(await screen.findByText('<script>not executed</script>')).toBeInTheDocument();
    expect(document.querySelector('.source-chunk script')).toBeNull();
    expect(screen.getByText('Similarity 0.750')).toBeInTheDocument();
    expect(screen.queryByText(/75%/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'View source page 2' })); expect(page).toHaveBeenCalledWith(2);
    expect(call).toHaveBeenCalledWith('/rag/search', expect.objectContaining({ body: { query: 'normalization', material_ids: [mid] } }));
  });
  it('reports insufficient evidence without generating an answer', async () => {
    call.mockImplementation(async (path: string) => path.endsWith('/search') ? { status: 'insufficient_evidence', sources: [] } : ready);
    render(<SourceSearch materialId={mid} onPage={vi.fn()} />); await screen.findByText('Ready to search'); search();
    expect(await screen.findByText(/No passage met/)).toHaveTextContent('No answer has been generated');
    expect(screen.queryByText('Retrieved source passages')).not.toBeInTheDocument();
  });
  it('recovers from a busy worker without showing stale results', async () => {
    call.mockImplementation(async (path: string) => { if (path.endsWith('/search')) throw new ApiError(409, 'RAG_BUSY'); return ready; });
    render(<SourceSearch materialId={mid} onPage={vi.fn()} />); await screen.findByText('Ready to search'); search();
    expect(await screen.findByRole('alert')).toHaveTextContent('Another local search');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Find passages' })).toBeEnabled());
  });
});
