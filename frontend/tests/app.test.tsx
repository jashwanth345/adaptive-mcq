import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { AuthProvider, useAuth } from '../src/auth';
import type { Role } from '../src/api';

const student = { id: 'fixture-id', email: 'learner@example.com', display_name: 'Test Learner', roles: ['student'] as Role[], created_at: '2026-10-05T00:00:00Z' };
function json(body: unknown, status = 200) { return new Response(body === undefined ? null : JSON.stringify(body), { status }); }
function mount(path = '/login') { return render(<MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>); }
function mockApi(roles: Role[] = ['student'], extras: Record<string, () => Response> = {}) {
  const user = { ...student, roles };
  const fetcher = vi.fn(async (url: string, _init?: RequestInit) => extras[url]?.() ?? (url.endsWith('/login') ? json({ access_token: 'fixture-token', expires_in: 900, user, token_type: 'bearer' }) : url.endsWith('/me') ? json(user) : json(undefined, 204)));
  vi.stubGlobal('fetch', fetcher); return fetcher;
}
it('opens a public landing page with working login navigation and honest test-mode copy', async () => {
  mockApi(); mount('/');
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Personalized practice.');
  expect(screen.getByText(/Current demonstration uses labelled test generation/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('link', { name: /^Login$/ }));
  expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
});
async function signIn() {
  await userEvent.type(screen.getByLabelText('Email address'), student.email);
  await userEvent.type(screen.getByLabelText('Password', { exact: true }), 'fixture-password');
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  await screen.findByRole('heading', { name: 'Welcome, Test.' });
}
describe('authentication and workspace foundation', () => {
  it('offers teacher registration and sends it to the isolated teacher signup endpoint', async () => {
    const fetcher = mockApi(); mount('/register');
    await userEvent.selectOptions(screen.getByLabelText('Account type'), 'teacher');
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Teacher Fixture' } });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'teacher@example.com' } });
    fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'Teacher fixture 42!' } });
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'Teacher fixture 42!' } });
    await userEvent.click(screen.getByRole('button', { name: 'Create teacher account' }));
    expect(await screen.findByText(/Your teacher account has been created/)).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/auth/register-teacher', expect.objectContaining({ body: JSON.stringify({ display_name: 'Teacher Fixture', email: 'teacher@example.com', password: 'Teacher fixture 42!' }) }));
  });
  it('redirects a protected deep link to sign in', async () => { mount('/account'); expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible(); });
  it('uses real server roles, shows working shortcuts and never persists the token', async () => {
    const fetcher = mockApi(); const storage = vi.spyOn(Storage.prototype, 'setItem'); mount(); await signIn();
    expect(screen.getByRole('link', { name: 'Student dashboard' })).toBeInTheDocument(); expect(screen.queryByRole('link', { name: 'Teacher dashboard' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create practice questions' })).toHaveAttribute('href', '/drafts'); expect(storage).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('link', { name: 'My account' })); expect(screen.getByText(student.email)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' })); expect(await screen.findByText('You have been signed out.')).toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/v1/auth/logout', expect.objectContaining({ headers: { Authorization: 'Bearer fixture-token' }, method: 'POST' }));
  });
  it('supports teacher and dual-role navigation from server identity', async () => { mockApi(['teacher', 'student']); mount(); await signIn(); expect(screen.getByRole('link', { name: 'Teacher dashboard' })).toHaveAttribute('aria-current', 'page'); await userEvent.click(screen.getByRole('link', { name: 'Student dashboard' })); expect(screen.getByRole('heading', { name: 'Take an assessment' })).toBeInTheDocument(); });
  it('creates student accounts without a role field and requires a separate sign in', async () => {
    const fetcher = mockApi(); mount('/register');
    await userEvent.type(screen.getByLabelText('Full name'), 'Test Learner'); await userEvent.type(screen.getByLabelText('Email address'), student.email); await userEvent.type(screen.getByLabelText('Password', { exact: true }), 'spaces are allowed'); await userEvent.type(screen.getByLabelText('Confirm password'), 'spaces are allowed');
    await userEvent.click(screen.getByRole('button', { name: 'Create student account' })); expect(await screen.findByRole('heading', { name: 'You’re ready to sign in' })).toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[0][1]?.body as string)).toEqual({ display_name: 'Test Learner', email: student.email, password: 'spaces are allowed' });
  });
  it('does not submit mismatched registration passwords', async () => {
    const fetcher = mockApi(); mount('/register'); fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Test' } }); fireEvent.change(screen.getByLabelText('Email address'), { target: { value: student.email } }); fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'first-long-password' } }); fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'other-long-password' } }); fireEvent.submit(screen.getByRole('form')); expect(await screen.findByRole('alert')).toHaveTextContent('do not match'); expect(fetcher).not.toHaveBeenCalled();
  });
  it.each([401, 409, 429, 503])('shows an actionable error for HTTP %s', async status => {
    mockApi([], { '/api/v1/auth/login': () => json({ error: { code: 'TEST' } }, status) }); mount(); fireEvent.change(screen.getByLabelText('Email address'), { target: { value: student.email } }); fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'wrong' } }); fireEvent.submit(screen.getByRole('form')); expect(await screen.findByRole('alert')).not.toBeEmptyDOMElement(); expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });
  it('retains the session when server logout fails so revocation can be retried', async () => { mockApi(['student'], { '/api/v1/auth/logout': () => json({}, 503) }); mount(); await signIn(); await userEvent.click(screen.getByRole('button', { name: 'Sign out' })); expect(await screen.findByRole('alert')).toHaveTextContent('not ready'); expect(screen.getByRole('heading', { name: 'Welcome, Test.' })).toBeInTheDocument(); });
  it('changes the password and returns to sign in without reporting an active session', async () => {
    const fetcher = mockApi(); mount(); await signIn(); await userEvent.click(screen.getByRole('link', { name: 'My account' }));
    fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'fixture-password' } }); fireEvent.change(screen.getByLabelText('New password', { exact: true }), { target: { value: ' next-password-123 ' } }); fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: ' next-password-123 ' } }); fireEvent.submit(screen.getByRole('form'));
    expect(await screen.findByText(/Password updated/)).toBeInTheDocument(); expect(fetcher).toHaveBeenLastCalledWith('/api/v1/auth/change-password', expect.objectContaining({ body: JSON.stringify({ current_password: 'fixture-password', new_password: ' next-password-123 ' }) }));
  });
  it('asks locally before revoking all sessions', async () => { const fetcher = mockApi(); mount(); await signIn(); await userEvent.click(screen.getByRole('link', { name: 'My account' })); await userEvent.click(screen.getByRole('button', { name: 'Sign out everywhere' })); expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/logout-all'))).toHaveLength(0); await userEvent.click(screen.getByRole('button', { name: 'Confirm sign out' })); expect(await screen.findByText('All sessions have been signed out.')).toBeInTheDocument(); });
  it('checks server session validity on focus and handles revoked tokens', async () => { mockApi(['student'], { '/api/v1/auth/me': () => json({}, 401) }); mount(); await signIn(); fireEvent(window, new Event('focus')); expect(await screen.findByText('Your session has ended. Please sign in again.')).toBeInTheDocument(); });
  it('makes unknown URLs recoverable', () => { mount('/missing'); expect(screen.getByRole('heading', { name: 'Let’s get you back on track.' })).toBeInTheDocument(); });
});

function Harness() { const auth = useAuth(); const go = useNavigate(); return <><button onClick={() => void auth.login(student.email, 'fixture-password')}>Test login</button><button onClick={() => go('/workspace/teacher')}>Teacher deep link</button><span data-testid="identity">{auth.user?.email ?? 'signed out'}</span></>; }
describe('session lifetime and route gates', () => {
  it('expires the in-memory session without a page interaction', async () => {
    vi.useFakeTimers(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ user: student, access_token: 'fixture', expires_in: 1 })));
    render(<MemoryRouter><AuthProvider><Harness /></AuthProvider></MemoryRouter>); fireEvent.click(screen.getByText('Test login')); await act(async () => { await vi.advanceTimersByTimeAsync(0); }); expect(screen.getByTestId('identity')).toHaveTextContent(student.email); await act(async () => { await vi.advanceTimersByTimeAsync(1001); }); expect(screen.getByTestId('identity')).toHaveTextContent('signed out');
  });
  it('rejects a manually entered teacher route for a student', async () => {
    mockApi(); render(<MemoryRouter initialEntries={['/login']}><AuthProvider><Harness /><App /></AuthProvider></MemoryRouter>); fireEvent.click(screen.getByText('Test login')); await waitFor(() => expect(screen.getByRole('heading', { name: 'Welcome, Test.' })).toBeInTheDocument()); fireEvent.click(screen.getByText('Teacher deep link')); expect(await screen.findByRole('heading', { name: 'This workspace is restricted' })).toBeInTheDocument();
  });
});



