import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiError, request } from '../src/api';
import { MathPreview, ValidationPanel, type ValidationReport } from '../src/generator/ValidationPanel';

const call = vi.fn();
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call }) }));
const id = '11111111-1111-4111-8111-111111111111';
const path = `/validation/drafts/${id}/reports`;
const report: ValidationReport = { id: 'report', technical_pass: false, publication_eligible: false, blockers: ['Test-generated content cannot be released.'], checks: [{ name: 'Question format', outcome: 'pass', detail: 'Format checked.' }], math: { status: 'not_applicable', computed: null, matching_options: [], detail: 'No explicit arithmetic.' }, duplicates: { status: 'fail', complete: true, scanned: 2, match_count: 1, matches: [{ version_id: id, kind: 'exact', similarity: 1 }], detail: 'Lexical checks only.' }, created_at: '2026-10-08T12:00:00Z' };

describe('validation workspace', () => {
  it('saves a blocked report and shows duplicates without approval controls', async () => {
    let saved = false;
    call.mockImplementation(async (_, options) => { if (options?.body) { saved = true; return report; } return { items: saved ? [report] : [], total: saved ? 1 : 0 }; });
    render(<ValidationPanel versionId={id} />);
    await screen.findByText('No saved validation reports yet.');
    await userEvent.click(screen.getByRole('button', { name: 'Run validation' }));
    expect(await screen.findByText('Release blocked')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Open validation 1' })).toBeInTheDocument();
    expect(screen.getByText('2 other questions checked · 1 candidate matches.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /approve|publish/i })).not.toBeInTheDocument();
  });
  it('retains retry keys and recovers from request failure', async () => {
    const keys: string[] = [];
    call.mockImplementation(async (_, options) => { if (options?.body) { keys.push(options.body.idempotency_key); throw new ApiError(503, 'DATABASE_UNAVAILABLE'); } return { items: [], total: 0 }; });
    render(<ValidationPanel versionId={id} />); await screen.findByText('No saved validation reports yet.');
    await userEvent.click(screen.getByRole('button', { name: 'Run validation' })); await screen.findByRole('alert');
    await userEvent.click(screen.getByRole('button', { name: 'Run validation' }));
    await waitFor(() => expect(keys).toHaveLength(2)); expect(keys[0]).toBe(keys[1]);
  });
  it('labels technical readiness as requiring human review and paginates snapshots', async () => {
    call.mockResolvedValue({ items: [{ ...report, technical_pass: true, blockers: [] }], total: 4 });
    render(<ValidationPanel versionId={id} />);
    expect(await screen.findByText('Technical checks passed · not approved')).toBeInTheDocument();
    expect(screen.getByText('This report does not approve or publish the question.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Older validations' }));
    await waitFor(() => expect(call).toHaveBeenCalledWith(`${path}?offset=3&limit=3`, expect.anything()));
  });
  it('checks an unsaved arithmetic example and clears stale results after edits', async () => {
    call.mockResolvedValue({ result: { status: 'pass', computed: '4', matching_options: [0], detail: 'Exact comparison.' } });
    render(<MathPreview />);
    await userEvent.click(screen.getByText('Try the arithmetic checker'));
    await userEvent.click(screen.getByRole('button', { name: 'Load arithmetic example' }));
    await userEvent.click(screen.getByRole('button', { name: 'Check arithmetic' }));
    expect(await screen.findByText('Arithmetic preview: pass')).toBeInTheDocument();
    expect(screen.getByText('Not saved · no release eligibility')).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith('/validation/math-check', expect.objectContaining({ body: { stem: 'Calculate: (3 + 5) / 2', options: ['4', '3', '5', '8'], correct_option: 0 } }));
    await userEvent.type(screen.getByLabelText('Math question'), '+1');
    expect(screen.queryByText('Arithmetic preview: pass')).not.toBeInTheDocument();
  });
  it('renders unsupported results and untrusted explanation as text', async () => {
    call.mockResolvedValue({ result: { status: 'unsupported', computed: null, matching_options: [], detail: '<script>unsafe</script>' } });
    render(<MathPreview />); await userEvent.click(screen.getByText('Try the arithmetic checker'));
    await userEvent.click(screen.getByRole('button', { name: 'Load arithmetic example' })); await userEvent.click(screen.getByRole('button', { name: 'Check arithmetic' }));
    expect(await screen.findByText('Arithmetic preview: unsupported')).toBeInTheDocument();
    expect(document.querySelector('.math-preview script')).toBeNull();
  });
  it('restricts validation requests to allowed local routes', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 })); vi.stubGlobal('fetch', fetcher);
    await request(path, { token: 'fixture', body: { idempotency_key: id } });
    expect(fetcher).toHaveBeenCalledWith(`/api/v1${path}`, expect.objectContaining({ credentials: 'omit', redirect: 'error' }));
    await expect(request(`${path}?owner=other`)).rejects.toThrow('Unsupported API path');
  });
});
