import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { Drafts } from '../src/generator/Drafts';
import { ApiError, request } from '../src/api';

const call = vi.fn();
// Review behavior is tested separately against its own API contracts.
vi.mock('../src/generator/ReviewPanel', () => ({ ReviewPanel: () => null }));
vi.mock('../src/generator/ValidationPanel', () => ({ ValidationPanel: () => null }));
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call }) }));
const mid = '11111111-1111-4111-8111-111111111111';
const id = '22222222-2222-4222-8222-222222222222';
const status = { mode: 'mock', ready: true, model: 'candidate', selection_status: 'Hardware-validated model selection: pending', error_code: null, hardware: { ram_gib: 7.77, available_ram_gib: 0.6 } };
const draft = { id, topic: 'normalization', stem: 'Test draft: which statement comes from the source?', options: ['<script>source text</script>', 'Placeholder B', 'Placeholder C', 'Placeholder D'], correct_option: 0, explanation: 'Deterministic fixture explanation, not verified.', difficulty: 'easy', cognitive_level: 'understand', mode: 'mock', status: 'unverified', retrieval: 'keyword_test', evidence_quote: 'Quoted source evidence.', source: { material_id: mid, title: 'Notes', citation: 'S1', page_start: 1, page_end: 1 }, created_at: '2026-10-07T12:00:00Z' };
function base(path: string) {
  if (path === '/generator/status') return status;
  if (path === '/materials?offset=0&limit=24') return { items: [{ id: mid, title: 'Notes' }], total: 1 };
  if (path.startsWith('/materials?')) return { items: [], total: 1 };
  if (path.includes('/drafts?')) return { items: [], total: 0 };
  return draft;
}
function mount() { return render(<MemoryRouter initialEntries={[`/drafts?material=${mid}`]}><Drafts /></MemoryRouter>); }
async function submit() { await screen.findByText('Test mode — no AI inference'); fireEvent.change(screen.getByLabelText('Draft topic'), { target: { value: 'normalization' } }); fireEvent.submit(screen.getByRole('form', { name: 'Create private draft' })); }

describe('private draft studio', () => {
  it.each([10, 30])('runs %s questions sequentially through indexing, generation, verification and validation', async count => {
    const steps: string[] = []; let generated = 0;
    call.mockImplementation(async (path: string, options?: { body?: { batch_index?: number }; method?: string }) => {
      if (path === '/generator/status' || path === '/verifier/status') return { ...status, mode: 'ollama' };
      if (path.endsWith('/index')) { steps.push('index'); return { state: 'ready' }; }
      if (path === '/generator/drafts' && options?.body) { steps.push('generate'); expect(options.body.batch_index).toBe(generated++); return { ...draft, id: `question-${generated}`, mode: 'ollama' }; }
      if (path.startsWith('/verifier/drafts/')) { steps.push('verify'); return { recommendation: 'PASS', ai_executed: true }; }
      if (path.startsWith('/validation/drafts/')) { steps.push('validate'); return { technical_pass: true }; }
      return base(path);
    }); mount();
    await screen.findByText(/Local AI mode/);
    fireEvent.change(screen.getByLabelText('Number of questions'), { target: { value: String(count) } });
    fireEvent.change(screen.getByLabelText('Draft topic'), { target: { value: 'normalization' } });
    fireEvent.submit(screen.getByRole('form', { name: 'Create private draft' }));
    await screen.findByText(`${count} drafts processed. Review the checks below; failed questions are not approved MCQs.`);
    expect(steps).toEqual(['index', ...Array.from({ length: count }, () => ['generate', 'verify', 'validate']).flat()]);
    expect(screen.getByRole('region', { name: 'Generated question set' })).toHaveTextContent(`${count} saved`);
  });
  it('resumes a failed verifier with the same key without regenerating the saved question', async () => {
    let generationCalls = 0; const reviewKeys: string[] = []; let failReview = true;
    call.mockImplementation(async (path: string, options?: { body?: { idempotency_key: string } }) => {
      if (path === '/generator/status' || path === '/verifier/status') return { ...status, mode: 'ollama' };
      if (path.endsWith('/index')) return { state: 'ready' };
      if (path === '/generator/drafts' && options?.body) return { ...draft, id: `q-${++generationCalls}`, mode: 'ollama' };
      if (path.startsWith('/verifier/drafts/')) { reviewKeys.push(options!.body!.idempotency_key); if (failReview) throw new ApiError(0, 'TIMEOUT'); return { recommendation: 'REJECT', ai_executed: true }; }
      if (path.startsWith('/validation/drafts/')) return { technical_pass: false };
      return base(path);
    }); mount(); await screen.findByText(/Local AI mode/);
    fireEvent.change(screen.getByLabelText('Draft topic'), { target: { value: 'normalization' } });
    fireEvent.submit(screen.getByRole('form', { name: 'Create private draft' }));
    await screen.findByText(/Stopped at question 1 of 10/); expect(generationCalls).toBe(1);
    failReview = false; await userEvent.click(screen.getByRole('button', { name: 'Generate 10 MCQs' }));
    await screen.findByText(/10 drafts processed/);
    expect(generationCalls).toBe(10); expect(reviewKeys[0]).toBe(reviewKeys[1]);
    expect(screen.getByRole('region', { name: 'Generated question set' })).toHaveTextContent('0 passed these checks');
  });
  it('does not offer placeholder batches as real MCQs', async () => {
    call.mockImplementation(async (path: string) => base(path)); mount();
    await screen.findByText('Test mode — no AI inference');
    expect(screen.getByRole('button', { name: 'Generate 10 MCQs' })).toBeDisabled();
    expect(screen.getByLabelText('Number of questions').querySelectorAll('option')).toHaveLength(21);
  });
  it('explains low memory while allowing PDF and count selection', async () => {
    call.mockImplementation(async (path: string) => path === '/generator/status'
      ? { ...status, mode: 'ollama', ready: false, error_code: 'GENERATOR_LOW_MEMORY', hardware: { available_ram_gib: 1.2 } } : base(path));
    mount();
    expect(await screen.findByText(/Free RAM: 1.2 GiB/)).toHaveTextContent('Readiness is checked again every 15 seconds');
    expect(screen.getByLabelText('Source document')).toBeEnabled();
    expect(screen.getByLabelText('Number of questions')).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Generate 10 MCQs' })).toBeDisabled();
  });
  it('labels test data, renders source content inertly and exposes no publication controls', async () => {
    call.mockImplementation(async (path: string) => base(path)); mount(); await submit();
    expect(await screen.findByText('Test draft — not AI-generated')).toBeInTheDocument();
    expect(screen.getByText('<script>source text</script>')).toBeInTheDocument();
    expect(document.querySelector('.draft-preview script')).toBeNull();
    expect(screen.getByText(/Proposed answer · unverified/)).toBeInTheDocument();
    expect(screen.getByText(/Test keyword selection/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /publish|approve|score/i })).not.toBeInTheDocument();
    expect(call).toHaveBeenCalledWith('/generator/drafts', expect.objectContaining({ body: expect.objectContaining({ material_ids: [mid], topic: 'normalization', idempotency_key: expect.any(String) }) }));
  });
  it('preserves idempotency on network retry and changes key after successful save', async () => {
    const keys: string[] = [];
    call.mockImplementation(async (path: string, options?: { body?: { idempotency_key: string } }) => {
      if (path === '/generator/drafts' && options?.body) { keys.push(options.body.idempotency_key); if (keys.length === 1) throw new ApiError(0, 'TIMEOUT'); }
      return base(path);
    }); mount(); await submit();
    expect(await screen.findByRole('alert')).toHaveTextContent('too long');
    await userEvent.click(screen.getByRole('button', { name: 'Create test draft' }));
    await screen.findByText('Test draft — not AI-generated'); expect(keys[0]).toBe(keys[1]);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Create test draft' })).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: 'Create test draft' }));
    await waitFor(() => expect(keys).toHaveLength(3)); expect(keys[2]).not.toBe(keys[1]);
  });
  it('keeps hardware-blocked AI mode disabled without changing to mock automatically', async () => {
    call.mockImplementation(async (path: string) => path === '/generator/status' ? { ...status, mode: 'ollama', ready: false, error_code: 'GENERATOR_LOW_MEMORY' } : base(path)); mount();
    expect(await screen.findByRole('alert')).toHaveTextContent('Not enough free RAM');
    expect(screen.getByRole('button', { name: 'Generate 10 MCQs' })).toBeDisabled();
    expect(screen.queryByText('Test mode — no AI inference')).not.toBeInTheDocument();
    expect(call.mock.calls.filter(([path]) => path === '/generator/drafts')).toHaveLength(0);
  });
  it('opens private history and explains rejected source evidence', async () => {
    call.mockImplementation(async (path: string) => path.includes('/drafts?') ? { items: [draft], total: 1 } : base(path)); mount();
    await userEvent.click(await screen.findByRole('button', { name: 'Open test draft: normalization' }));
    expect(await screen.findByText('Quoted source evidence.')).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith(`/generator/drafts/${id}`, expect.anything());
    call.mockImplementation(async (path: string, options?: { body?: unknown }) => { if (options?.body) throw new ApiError(422, 'GENERATOR_EVIDENCE_MISMATCH'); return base(path); });
    await submit(); expect(await screen.findByRole('alert')).toHaveTextContent('No draft was saved');
    expect(screen.queryByText('Quoted source evidence.')).not.toBeInTheDocument();
  });
  it('keeps new API routes same-origin and rejects malformed paths', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 })); vi.stubGlobal('fetch', fetcher);
    await request('/generator/status', { token: 'fixture' });
    expect(fetcher).toHaveBeenCalledWith('/api/v1/generator/status', expect.objectContaining({ credentials: 'omit', redirect: 'error' }));
    await expect(request('/generator/drafts?owner=other')).rejects.toThrow('Unsupported API path');
  });
});

