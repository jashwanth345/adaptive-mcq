import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { AuthProvider } from '../src/auth';

const student = { id: '11111111-1111-4111-8111-111111111111', email: 'student@example.com', display_name: 'Test Student', roles: ['student'], created_at: '2026-10-06T09:00:00Z' };
const summary = { preferences: { preferred_difficulty: 'easy' }, counts: { courses: 0, materials: 0, submitted_attempts: 0, feedback: 0 }, courses: [] };
const history = { items: [], total: 0, offset: 0, limit: 6 };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
function setup(handler?: (path: string, init: RequestInit) => Response | Promise<Response> | undefined) {
  const fetcher = vi.fn(async (path: string, init: RequestInit) => {
    const custom = handler?.(path, init); if (custom) return custom;
    if (path.endsWith('/login')) return json({ access_token: 'student-token', user: student, expires_in: 900 });
    if (path.endsWith('/me')) return json(student);
    if (path.endsWith('/dashboard')) return json(summary);
    if (path.includes('/attempts?')) return json(history);
    return json(JSON.parse(init.body as string));
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={['/login']}><AuthProvider><App /></AuthProvider></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: student.email } }); fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'fixture password' } }); fireEvent.submit(screen.getByRole('form'));
  return fetcher;
}
describe('student dashboard', () => {
  it('shows stored empty counts without invented scores or mastery', async () => {
    setup(); expect(await screen.findByText('No enrolled courses yet')).toBeInTheDocument(); expect(screen.getByLabelText('Submitted attempts: 0')).toBeInTheDocument(); expect(screen.getByText('Your learning history starts here')).toBeInTheDocument(); expect(screen.getByRole('radio', { name: 'Easy' })).toBeChecked(); expect(screen.getByRole('button', { name: 'Save preference' })).toBeDisabled(); expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
  });
  it('saves the selected preference without submitting a student ID', async () => {
    const fetcher = setup(); await screen.findByRole('radio', { name: 'Easy' }); await userEvent.click(screen.getByRole('radio', { name: 'Medium' })); await userEvent.click(screen.getByRole('button', { name: 'Save preference' })); expect(await screen.findByText('Practice preference saved.')).toBeInTheDocument(); expect(fetcher).toHaveBeenCalledWith('/api/v1/student/preferences', expect.objectContaining({ headers: { Authorization: 'Bearer student-token', 'Content-Type': 'application/json' }, body: JSON.stringify({ preferred_difficulty: 'medium' }) })); expect(screen.getByRole('button', { name: 'Save preference' })).toBeDisabled();
  });
  it('retains the unsaved preference after a failed write', async () => {
    setup(path => path.endsWith('/preferences') ? json({}, 503) : undefined); await screen.findByRole('radio', { name: 'Easy' }); await userEvent.click(screen.getByRole('radio', { name: 'Hard' })); await userEvent.click(screen.getByRole('button', { name: 'Save preference' })); expect(await screen.findByRole('alert')).toHaveTextContent('not ready'); expect(screen.getByRole('radio', { name: 'Hard' })).toBeChecked(); expect(screen.getByText('Unsaved change')).toBeInTheDocument(); expect(screen.queryByText('Practice preference saved.')).not.toBeInTheDocument();
  });
  it('keeps failed data unavailable and recovers through retry', async () => {
    let failed = true; setup(path => path.endsWith('/dashboard') && failed ? json({}, 503) : undefined); await screen.findByRole('alert'); expect(screen.queryByLabelText('Enrolled courses: 0')).not.toBeInTheDocument(); expect(screen.getByLabelText('Enrolled courses: unavailable')).toBeInTheDocument(); failed = false; await userEvent.click(screen.getByRole('button', { name: 'Retry student dashboard' })); expect(await screen.findByLabelText('Enrolled courses: 0')).toBeInTheDocument();
  });
  it('renders stored enrollments and metadata-only history with pagination', async () => {
    const item = { id: student.id, title: 'Database review', kind: 'classroom', state: 'submitted', attempt_number: 1, started_at: student.created_at, submitted_at: student.created_at };
    const fetcher = setup(path => path.endsWith('/dashboard') ? json({ ...summary, counts: { ...summary.counts, courses: 1 }, courses: [{ id: student.id, title: 'DBMS', joined_at: student.created_at }] }) : path.includes('/attempts?') ? json({ ...history, total: 7, items: [item] }) : undefined);
    expect(await screen.findByText('DBMS')).toBeInTheDocument(); expect(screen.getByRole('cell', { name: 'Submitted' })).toBeInTheDocument(); expect(screen.queryByRole('columnheader', { name: /score/i })).not.toBeInTheDocument(); await userEvent.click(screen.getByRole('button', { name: 'Next attempts' })); await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/v1/student/attempts?offset=6&limit=6', expect.anything()));
  });
  it('returns to sign-in after the dashboard rejects a session', async () => {
    setup(path => path.endsWith('/dashboard') ? json({}, 401) : undefined); expect(await screen.findByText('Your session has ended. Please sign in again.')).toBeInTheDocument();
  });
});
