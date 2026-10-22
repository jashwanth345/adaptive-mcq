import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiError, request } from '../src/api';
import { ReviewPanel, type Review } from '../src/generator/ReviewPanel';

const call = vi.fn();
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call }) }));
const version = '11111111-1111-4111-8111-111111111111';
const path = `/verifier/drafts/${version}/reports`;
const status = { mode: 'mock', ready: true, configured_same_model: true, error_code: null };
const report: Review = { id: 'report-1', mode: 'mock', recommendation: 'NOT_EVALUATED', publication_eligible: false, checks: [{ name: 'Question format', outcome: 'pass', detail: 'Four options.' }, { name: 'AI quality review', outcome: 'not_evaluated', detail: 'No LLM ran.' }], reason: 'Test only. No AI quality evaluation.', ai_executed: false, blind_option: null, model_relationship: 'not_evaluated', pending: ['Teacher review'], created_at: '2026-10-07T12:00:00Z' };
function mount(mode = 'mock') { return render(<ReviewPanel versionId={version} draftMode={mode} />); }

describe('advisory draft reviews', () => {
  it('creates and reloads an explicitly non-AI report without approval controls', async () => {
    let saved = false;
    call.mockImplementation(async (url: string, options?: { body?: unknown }) => {
      if (url.endsWith('/status')) return status;
      if (options?.body) { saved = true; return report; }
      return { items: saved ? [report] : [], total: saved ? 1 : 0 };
    }); mount();
    expect(await screen.findByText('No saved review reports yet.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Run test review' }));
    expect(await screen.findByText('Test report · AI quality not evaluated')).toBeInTheDocument();
    expect(screen.getByText('Publication status: not approved')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Open test report 1' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /approve|publish/i })).not.toBeInTheDocument();
    expect(call).toHaveBeenCalledWith(path, expect.objectContaining({ body: { idempotency_key: expect.any(String) } }));
  });
  it('retains the retry key after a failed response', async () => {
    const keys: string[] = [];
    call.mockImplementation(async (url: string, options?: { body?: { idempotency_key: string } }) => {
      if (url.endsWith('/status')) return status;
      if (options?.body) { keys.push(options.body.idempotency_key); throw new ApiError(0, 'TIMEOUT'); }
      return { items: [], total: 0 };
    }); mount(); await screen.findByText('No saved review reports yet.');
    await userEvent.click(screen.getByRole('button', { name: 'Run test review' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('too long');
    await userEvent.click(screen.getByRole('button', { name: 'Run test review' }));
    await waitFor(() => expect(keys).toHaveLength(2)); expect(keys[0]).toBe(keys[1]);
  });
  it('blocks real AI review for a mock draft without sending a request', async () => {
    call.mockImplementation(async (url: string) => url.endsWith('/status') ? { ...status, mode: 'ollama' } : { items: [], total: 0 }); mount();
    expect(await screen.findByText(/Real AI review is unavailable for test content/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run local AI review' })).toBeDisabled();
    expect(call.mock.calls.some(([, options]) => options?.body)).toBe(false);
  });
  it('shows saved AI recommendations as advisory with same-checkpoint disclosure', async () => {
    const ai = { ...report, mode: 'ollama', recommendation: 'PASS', ai_executed: true, blind_option: 0, model_relationship: 'same_checkpoint', reason: '<script>inert rationale</script>' };
    call.mockImplementation(async (url: string) => url.endsWith('/status') ? { ...status, mode: 'disabled', ready: false } : { items: [ai], total: 1 }); mount('ollama');
    expect(await screen.findByText('AI recommendation: PASS')).toBeInTheDocument();
    expect(screen.getByText('Publication status: not approved')).toBeInTheDocument();
    expect(screen.getByText(/independent-model verification is not established/)).toBeInTheDocument();
    expect(document.querySelector('.draft-review script')).toBeNull();
    expect(screen.getByRole('button', { name: 'Run local AI review' })).toBeDisabled();
  });
  it('recovers from a history-loading error and paginates reports', async () => {
    let ready = false;
    call.mockImplementation(async (url: string) => { if (!ready) throw new ApiError(503, 'DATABASE_UNAVAILABLE'); return url.endsWith('/status') ? status : { items: [report], total: 4 }; }); mount();
    await screen.findByRole('alert'); ready = true;
    await userEvent.click(screen.getByRole('button', { name: 'Refresh reviews' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Older reports' }));
    await waitFor(() => expect(call).toHaveBeenCalledWith(`${path}?offset=3&limit=3`, expect.anything()));
  });
  it('restricts new routes to same-origin and rejects extra query parameters', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 })); vi.stubGlobal('fetch', fetcher);
    await request(path, { token: 'fixture', body: { idempotency_key: version } });
    expect(fetcher).toHaveBeenCalledWith(`/api/v1${path}`, expect.objectContaining({ credentials: 'omit', redirect: 'error' }));
    await expect(request(`${path}?owner=someone`)).rejects.toThrow('Unsupported API path');
  });
});
