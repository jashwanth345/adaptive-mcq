import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, request } from '../src/api';
import { JoinAssessment, TeacherAssessments } from '../src/assessments/Assessments';

const call = vi.fn(); let roles = ['teacher'];
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call, user: { roles } }) }));
const id = '11111111-1111-4111-8111-111111111111'; const version = '22222222-2222-4222-8222-222222222222';
const base = { id, title: 'Database assessment', state: 'draft', question_count: 1, revision: 1, course_id: id, can_publish: false, issued_code: null as string | null, time_limit_seconds: null, max_attempts: 1, randomize_questions: false, randomize_options: false, release_policy: 'after_submit', questions: [{ version_id: version, position: 1, version: 1, stem: 'Which method reduces redundant data?', state: 'pending', mode: 'mock' }], participants: [] as {student_id: string; email: string; display_name: string; active: boolean}[], codes: [] as {id: string; expires_at: string; revoked_at: string | null; active: boolean}[] };
let active = structuredClone(base);
function load(path: string) {
  if (path.startsWith('/teacher/courses')) return { items: [{ id, title: 'Database systems' }], total: 1 };
  if (path.startsWith('/teacher/reviews')) return { items: [{ id: version, version: 1, stem: base.questions[0].stem, mode: 'mock', state: 'pending' }], total: 1 };
  if (path.includes('?offset')) return { items: [active], total: 1 };
  return active;
}
function mount(student = false) { return render(<MemoryRouter>{student ? <JoinAssessment /> : <TeacherAssessments />}</MemoryRouter>); }
beforeEach(() => { call.mockClear(); roles = ['teacher']; active = structuredClone(base); call.mockImplementation(async path => load(path)); });

describe('assessment publication', () => {
  it('creates and selects a course without losing the assessment title', async () => {
    const created = { id: 'new-course', title: 'Prompt Engineering' };
    call.mockImplementation(async (path, options) => path === '/teacher/courses' && options?.body ? created : load(path));
    mount(); await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    await screen.findByRole('option', { name: 'Database systems' });
    await userEvent.type(screen.getByLabelText('Assessment title'), 'PE assessment');
    await userEvent.click(screen.getByText('Create a course here'));
    await userEvent.type(screen.getByLabelText('New course title'), created.title);
    await userEvent.click(screen.getByRole('button', { name: 'Create and select course' }));
    await waitFor(() => expect(screen.getByLabelText('Course')).toHaveValue(created.id));
    expect(screen.getByLabelText('Assessment title')).toHaveValue('PE assessment');
    expect(screen.getByRole('button', { name: 'Save new assessment' })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('select at least one question');
  });
  it('creates a draft from owned questions and keeps mock publication disabled', async () => {
    call.mockImplementation(async (path, options) => options?.body ? active : load(path)); mount();
    await userEvent.click(screen.getByRole('button', { name: 'Create assessment' }));
    const form = screen.getByRole('form', { name: 'Assessment draft' });
    expect(within(form).getByRole('status')).toHaveTextContent('select a course and select at least one question');
    await userEvent.type(within(form).getByLabelText('Assessment title'), 'Database assessment');
    await screen.findByRole('option', { name: 'Database systems' });
    await userEvent.selectOptions(within(form).getByLabelText('Course'), id);
    await userEvent.click(within(form).getByRole('checkbox', { name: /Which method/ }));
    await userEvent.click(within(form).getByRole('button', { name: 'Save new assessment' }));
    expect(await screen.findByRole('button', { name: 'Publish assessment' })).toBeDisabled();
    expect(call).toHaveBeenCalledWith('/teacher/assessments', expect.objectContaining({ body: expect.objectContaining({ version_ids: [version], course_id: id, max_attempts: 1, idempotency_key: expect.any(String) }) }));
  });
  it('requires confirmation and shows the issued code only after publication succeeds', async () => {
    active.can_publish = true; active.questions[0].mode = 'ollama';
    call.mockImplementation(async (path, options) => { if (options?.body) { active = { ...active, state: 'published', can_publish: false, issued_code: 'MCQ-1234-5678-ABCD-EF01-2345', codes: [{ id, active: true, expires_at: '2026-10-10T12:00:00Z', revoked_at: null }] }; return active; } return load(path); });
    mount(); await userEvent.click(await screen.findByRole('button', { name: /Database assessment/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Publish assessment' }));
    expect(call.mock.calls.filter(([, options]) => options?.body)).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: 'Confirm publish' }));
    expect(await screen.findByText('MCQ-1234-5678-ABCD-EF01-2345')).toBeInTheDocument();
    expect(screen.queryByText('Edit assessment draft')).not.toBeInTheDocument();
    expect(call).toHaveBeenCalledWith(`/teacher/assessments/${id}/publish`, expect.objectContaining({ body: expect.objectContaining({ revision: 1, expiry_hours: 24 }) }));
  });
  it('keeps the same retry key after publication failure', async () => {
    active.can_publish = true; const keys: string[] = [];
    call.mockImplementation(async (path, options) => { if (options?.body) { keys.push(options.body.idempotency_key); throw new ApiError(409, 'ASSESSMENT_BLOCKED'); } return load(path); });
    mount(); await userEvent.click(await screen.findByRole('button', { name: /Database assessment/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Publish assessment' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm publish' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Publication is blocked');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm publish' }));
    await waitFor(() => expect(keys).toHaveLength(2)); expect(keys[0]).toBe(keys[1]);
    expect(screen.queryByRole('button', { name: 'Copy reference code' })).not.toBeInTheDocument();
  });
  it('allows a registered email without sending a message', async () => {
    call.mockImplementation(async (path, options) => { if (options?.body) return { ...active, participants: [{ student_id: id, display_name: 'Student', email: 'learner@example.com', active: true }] }; return load(path); });
    mount(); await userEvent.click(await screen.findByRole('button', { name: /Database assessment/ }));
    await userEvent.type(await screen.findByLabelText('Student email'), 'learner@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Allow student' }));
    expect(await screen.findByRole('button', { name: 'Remove access for learner@example.com' })).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith(`/teacher/assessments/${id}/participants`, expect.objectContaining({ body: expect.objectContaining({ email: 'learner@example.com', active: true }) }));
  });
  it('requires confirmation before revoking a published code', async () => {
    active.state = 'published'; active.codes = [{ id, active: true, expires_at: '2026-10-10T12:00:00Z', revoked_at: null }];
    call.mockImplementation(async (path, options) => options?.body ? { ...active, codes: [] } : load(path));
    mount(); await userEvent.click(await screen.findByRole('button', { name: /Database assessment/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Revoke codes' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm revoke' }));
    expect(await screen.findByText('Reference codes revoked. New access is blocked.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Revoke codes' })).toBeDisabled();
  });
  it('guards teacher and student page roles', () => {
    roles = ['student']; const view = mount(); expect(screen.getByText('Teacher access required')).toBeInTheDocument(); expect(call).not.toHaveBeenCalled();
    view.unmount(); roles = ['teacher']; mount(true); expect(screen.getByText('Student access required')).toBeInTheDocument(); expect(call).not.toHaveBeenCalled();
  });
});

describe('student reference code', () => {
  it('submits a code in the body, clears it after joining and does not start an attempt', async () => {
    roles = ['student']; const admitted = { ...base, available: true }; call.mockImplementation(async (_path, options) => options?.body ? admitted : { items: [], total: 0 });
    mount(true); await userEvent.type(screen.getByLabelText('Reference code'), 'MCQ-1234-5678-ABCD-EF01-2345');
    await userEvent.click(screen.getByRole('button', { name: 'Join assessment' }));
    expect(await screen.findByRole('status')).toHaveTextContent('You joined Database assessment');
    expect(screen.getByLabelText('Reference code')).toHaveValue('');
    expect(call).toHaveBeenCalledWith('/student/assessments/join', expect.objectContaining({ body: { code: 'MCQ-1234-5678-ABCD-EF01-2345' } }));
    expect(call.mock.calls.every(([path]) => !path.includes('1234') && !path.includes('/attempts'))).toBe(true);
    expect(screen.queryByRole('button', { name: /Start attempt/ })).not.toBeInTheDocument();
  });
  it('shows the safe rejection and preserves code for correction', async () => {
    roles = ['student']; call.mockImplementation(async (_path, options) => { if (options?.body) throw new ApiError(404, 'ASSESSMENT_UNAVAILABLE'); return { items: [], total: 0 }; });
    mount(true); await userEvent.type(screen.getByLabelText('Reference code'), 'wrong-code'); await userEvent.click(screen.getByRole('button', { name: 'Join assessment' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Check the code'); expect(screen.getByLabelText('Reference code')).toHaveValue('wrong-code');
  });
  it('keeps codes out of URLs and limits allowed API paths', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    await request('/student/assessments/join', { token: 'fixture', body: { code: 'fixture-code' } });
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/student/assessments/join', expect.objectContaining({ method: 'POST', cache: 'no-store' }));
    await expect(request('/student/assessments?code=secret')).rejects.toThrow('Unsupported');
    await expect(request('/teacher/assessments/../../evil')).rejects.toThrow('Unsupported');
  });
});
