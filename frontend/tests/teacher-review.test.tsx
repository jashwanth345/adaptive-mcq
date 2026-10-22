import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, request } from '../src/api';
import { TeacherReview } from '../src/teacher/TeacherReview';

const call = vi.fn(); let roles = ['teacher'];
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call, user: { roles } }) }));
vi.mock('../src/generator/ReviewPanel', () => ({ ReviewPanel: () => <p>AI review panel</p> }));
vi.mock('../src/generator/ValidationPanel', () => ({ ValidationPanel: () => <p>Validation panel</p> }));
const id = '11111111-1111-4111-8111-111111111111'; const next = '22222222-2222-4222-8222-222222222222';
const draft = { id, stem: 'Which process reduces redundant data?', options: ['Normalization', 'Replication', 'Indexing', 'Sorting'], correct_option: 0, explanation: 'Normalization reduces redundant data.', difficulty: 'easy', cognitive_level: 'understand', mode: 'mock', evidence_quote: 'Normalization reduces redundant data.', source: { title: 'DBMS source', page_start: 1 } };
const detail = { draft, version: 1, current: true, state: 'pending', can_approve: false, blocker: 'Test-generated content cannot be approved, including after editing.' };
let active = detail;
function load(path: string) {
  if (path.includes('/versions')) return { items: [{ id: active.draft.id, version: active.version, events: [] }], total: 1 };
  if (path.includes('?offset') && !path.includes('/versions')) return { items: [{ ...active.draft, version: active.version, state: active.state, topic: 'DBMS' }], total: 1 };
  return active;
}
function mount() { return render(<MemoryRouter initialEntries={[`/teacher-review?version=${id}`]}><TeacherReview /></MemoryRouter>); }
beforeEach(() => { call.mockClear(); roles = ['teacher']; active = structuredClone(detail); call.mockImplementation(async path => load(path)); });

describe('teacher review workflow', () => {
  it('keeps mock approval disabled and displays its source and review tools', async () => {
    mount(); await screen.findByRole('heading', { name: 'Version 1' });
    expect(screen.getByText('DBMS source')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Teacher review note'), 'Reviewed source');
    expect(screen.getByRole('button', { name: 'Approve this version' })).toBeDisabled();
    expect(screen.getByText('AI review panel')).toBeInTheDocument();
  });
  it('saves a new version and clears earlier approval state', async () => {
    call.mockImplementation(async (path, options) => {
      if (options?.body) { active = { ...detail, version: 2, draft: { ...draft, id: next, stem: options.body.stem } }; return active; }
      return load(path);
    });
    mount(); await screen.findByRole('heading', { name: 'Version 1' });
    await userEvent.click(screen.getByText('Edit as a new version'));
    const form = screen.getByRole('form', { name: 'Edit question version' });
    await userEvent.clear(within(form).getByLabelText('Question'));
    await userEvent.type(within(form).getByLabelText('Question'), 'Which method reduces redundant data?');
    await userEvent.type(within(form).getByLabelText('Reason for this edit'), 'Clarify wording');
    await userEvent.click(within(form).getByRole('button', { name: 'Save new version' }));
    expect(await screen.findByText('Version 2 saved. Fresh review and validation are required.')).toBeInTheDocument();
    await screen.findByRole('heading', { name: 'Version 2' });
    expect(call).toHaveBeenCalledWith(`/teacher/reviews/${id}/edits`, expect.objectContaining({ body: expect.objectContaining({ stem: 'Which method reduces redundant data?', correct_option: 0, idempotency_key: expect.any(String) }) }));
    expect(screen.getByRole('button', { name: 'Approve this version' })).toBeDisabled();
  });
  it('requires explicit approval confirmation and uses the teacher note', async () => {
    active = { ...detail, draft: { ...draft, mode: 'ollama' }, can_approve: true, blocker: '' };
    call.mockImplementation(async (path, options) => { if (options?.body) { active = { ...active, state: 'approved' }; return active; } return load(path); });
    mount(); await screen.findByLabelText('Teacher review note');
    await userEvent.type(screen.getByLabelText('Teacher review note'), 'Source and all options checked');
    await userEvent.click(screen.getByRole('button', { name: 'Approve this version' }));
    expect(call.mock.calls.filter(([, options]) => options?.body)).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: 'Confirm approval' }));
    expect(await screen.findByText('Teacher approval saved. No assessment has been published.')).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith(`/teacher/reviews/${id}/decisions`, expect.objectContaining({ body: expect.objectContaining({ action: 'approve', note: 'Source and all options checked' }) }));
  });
  it('retains a retry key on a failed decision and displays a useful conflict', async () => {
    const keys: string[] = [];
    call.mockImplementation(async (path, options) => { if (options?.body) { keys.push(options.body.idempotency_key); throw new ApiError(409, 'TEACHER_REVIEW_STALE'); } return load(path); });
    mount(); await screen.findByLabelText('Teacher review note');
    await userEvent.type(screen.getByLabelText('Teacher review note'), 'Question is ambiguous');
    await userEvent.click(screen.getByRole('button', { name: 'Reject this version' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('A newer version exists');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }));
    await waitFor(() => expect(keys).toHaveLength(2)); expect(keys[0]).toBe(keys[1]);
  });
  it('does not expose edit or decision actions on superseded versions', async () => {
    active = { ...detail, current: false, blocker: 'Open the latest version.' }; mount();
    await screen.findByText('Open the latest version.');
    expect(screen.queryByText('Edit as a new version')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve this version' })).not.toBeInTheDocument();
  });
  it('does not fetch teacher content for students', () => {
    roles = ['student']; mount(); expect(screen.getByText('Teacher access required')).toBeInTheDocument(); expect(call).not.toHaveBeenCalled();
  });
  it('limits approval requests to the fixed local API route', async () => {
    const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 200 }));
    await request(`/teacher/reviews/${id}/decisions`, { token: 'fixture', body: { action: 'approve' } });
    expect(fetcher).toHaveBeenCalledWith(`/api/v1/teacher/reviews/${id}/decisions`, expect.objectContaining({ credentials: 'omit', redirect: 'error' }));
    await expect(request('https://example.com/teacher/reviews')).rejects.toThrow('Unsupported API path');
  });
});
