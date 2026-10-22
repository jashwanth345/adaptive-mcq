import { fireEvent, render as renderView, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Materials } from '../src/materials/Materials';
import { ApiError } from '../src/api';

const call = vi.fn();
const render = (view: ReactNode) => renderView(<MemoryRouter>{view}</MemoryRouter>);
// Retrieval behavior is covered in rag.test.tsx and the real-browser suite.
vi.mock('../src/materials/SourceSearch', () => ({ SourceSearch: () => null }));
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call }) }));
const item = { id: '11111111-1111-4111-8111-111111111111', title: 'DBMS notes', page_count: 2, byte_size: 1200, chunk_count: 1 };
const listing = { items: [item], total: 1, offset: 0, limit: 6 };
async function upload() {
  fireEvent.change(screen.getByLabelText('Material title'), { target: { value: 'DBMS notes' } });
  await userEvent.upload(screen.getByLabelText('Choose PDF'), new File(['%PDF-test'], 'notes.pdf', { type: 'application/pdf' }));
  fireEvent.submit(screen.getByRole('form', { name: 'Upload study PDF' }));
}
describe('private material library', () => {
  it('accepts a dropped PDF, suggests its title and explains OCR provenance', async () => {
    call.mockImplementation(async (path: string) => path.includes('title=') ? { id: item.id, reused: false } : path.includes(item.id) ? { ...item, page: 1, empty_pages: [], ocr_pages: [1], chunks: [{ ordinal: 0, content: 'Recognized text' }] } : { ...listing, items: [], total: 0 });
    render(<Materials />); await screen.findByText('Your library starts here');
    const file = new File(['%PDF-scan'], 'Scanned notes.pdf', { type: 'application/pdf' });
    fireEvent.drop(screen.getByText('Drag & drop your PDF here').closest('label')!, { dataTransfer: { files: [file] } });
    expect(screen.getByLabelText('Material title')).toHaveValue('Scanned notes');
    await userEvent.click(screen.getByRole('button', { name: 'Upload and process' }));
    expect(await screen.findByText(/Scanned text recognized on pages 1/)).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith('/materials?title=Scanned%20notes', expect.objectContaining({ body: file }));
  });
  it('rejects an oversized drop before sending any upload', async () => {
    call.mockResolvedValue(listing); render(<Materials />); await screen.findByText('1 processed document');
    const file = new File(['x'], 'large.pdf', { type: 'application/pdf' }); Object.defineProperty(file, 'size', { value: 6 * 1024 * 1024 });
    fireEvent.drop(screen.getByText('Drag & drop your PDF here').closest('label')!, { dataTransfer: { files: [file] } });
    expect(screen.getByRole('alert')).toHaveTextContent('no larger than 5 MiB');
    expect(call.mock.calls.some(([path]) => path.includes('title='))).toBe(false);
  });
  it('shows empty library with truthful planned status', async () => {
    call.mockResolvedValue({ ...listing, items: [], total: 0 }); render(<Materials />);
    expect(await screen.findByText('Your library starts here')).toBeInTheDocument();
    expect(screen.getByText(/Local source search is available below/)).toBeInTheDocument();
  });
  it('uploads a PDF and renders page text safely with empty-page warnings', async () => {
    call.mockImplementation(async (path: string) => path.includes('title=') ? { id: item.id, reused: false } : path.includes(item.id) ? { ...item, page: 1, empty_pages: [2], chunks: [{ ordinal: 0, content: '<script>not executed</script>' }] } : listing);
    render(<Materials />); await screen.findByText('1 processed document'); await upload();
    expect(await screen.findByText('PDF saved. Extracted text is ready to review.')).toBeInTheDocument();
    expect(await screen.findByText('<script>not executed</script>')).toBeInTheDocument();
    expect(document.querySelector('.source-chunk script')).toBeNull();
    expect(screen.getByText(/Pages without extractable text: 2/)).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith('/materials?title=DBMS%20notes', expect.objectContaining({ body: expect.any(File) }));
    await userEvent.click(screen.getByRole('button', { name: 'Next page' }));
    expect(call).toHaveBeenCalledWith(`/materials/${item.id}?page=2`, expect.anything());
  });
  it('retains the upload form and explains an image-only PDF failure', async () => {
    call.mockImplementation(async (path: string) => { if (path.includes('title=')) throw new ApiError(422, 'PDF_NO_TEXT'); return listing; });
    render(<Materials />); await screen.findByText('1 processed document'); await upload();
    expect(await screen.findByRole('alert')).toHaveTextContent('No extractable text');
    expect(screen.getByLabelText('Material title')).toHaveValue('DBMS notes');
    expect(screen.getByRole('button', { name: 'Upload and process' })).toBeEnabled();
  });
  it('keeps unavailable library distinct from an empty library and retries', async () => {
    call.mockRejectedValue(new ApiError(503, 'DATABASE_UNAVAILABLE')); render(<Materials />);
    await screen.findByRole('alert'); expect(screen.queryByText('Your library starts here')).not.toBeInTheDocument();
    call.mockResolvedValue(listing); await userEvent.click(screen.getByRole('button', { name: 'Refresh library' }));
    expect(await screen.findByText('DBMS notes')).toBeInTheDocument();
  });
});
