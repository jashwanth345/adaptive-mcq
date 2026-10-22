import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { AuthProvider } from '../src/auth';

const id = '11111111-1111-4111-8111-111111111111';
const course = { id, title: 'Database Systems', created_at: '2026-10-06T09:00:00Z', topic_count: 0 };
const teacher = { id, email: 'teacher@example.com', display_name: 'Test Teacher', roles: ['teacher'], created_at: course.created_at };
const dashboard = { counts: { courses: 0, materials: 0, questions: 0, assessments: 0 }, recent_assessments: [] };
const page = { items: [], total: 0, offset: 0, limit: 6 };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
function setup(handler?: (path: string, options: RequestInit) => Response | Promise<Response> | undefined) {
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    const special = handler?.(path, options); if (special) return special;
    if (path.endsWith('/login')) return json({ user: teacher, access_token: 'teacher-token', expires_in: 900 });
    if (path.endsWith('/me')) return json(teacher);
    if (path.endsWith('/dashboard')) return json(dashboard);
    if (path.includes('/courses?')) return json(page);
    if (path.endsWith('/courses') && options.method === 'POST') return json(course, 201);
    if (path.endsWith('/topics')) return json({ id, name: 'Joins' }, 201);
    return json({ ...course, topics: [] });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={['/login']}><AuthProvider><App /></AuthProvider></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: teacher.email } });
  fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'teacher password' } });
  fireEvent.submit(screen.getByRole('form'));
  return fetcher;
}
describe('teacher dashboard', () => {
  it('shows stored zero counts with honest empty states', async () => {
    const fetcher = setup(); expect(await screen.findByText('Your first course starts here')).toBeInTheDocument();
    expect(screen.getByLabelText('Your courses: 0')).toBeVisible(); expect(screen.getByText('No classroom assessments yet')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/teacher/dashboard', expect.objectContaining({ headers: { Authorization: 'Bearer teacher-token' } }));
  });
  it('shows unavailable values on failure and recovers on retry', async () => {
    let fail = true; setup(path => path.endsWith('/dashboard') && fail ? json({ error: { code: 'DATABASE_UNAVAILABLE' } }, 503) : undefined);
    expect(await screen.findByRole('alert')).toHaveTextContent('not ready'); expect(screen.queryByLabelText('Your courses: 0')).not.toBeInTheDocument(); expect(screen.getByLabelText('Your courses: unavailable')).toBeInTheDocument();
    fail = false; await userEvent.click(screen.getByRole('button', { name: 'Retry dashboard' })); expect(await screen.findByLabelText('Your courses: 0')).toBeInTheDocument();
  });
  it('saves a trimmed course then opens its topic editor', async () => {
    const fetcher = setup(); await screen.findByText('Your first course starts here'); await userEvent.click(screen.getByRole('button', { name: 'Create course' }));
    await userEvent.type(screen.getByLabelText('Course title'), '  Database Systems  '); await userEvent.click(screen.getByRole('button', { name: 'Save course' }));
    expect(await screen.findByRole('heading', { name: 'Database Systems' })).toBeInTheDocument(); expect(fetcher).toHaveBeenCalledWith('/api/v1/teacher/courses', expect.objectContaining({ body: JSON.stringify({ title: 'Database Systems' }) }));
    await userEvent.type(screen.getByLabelText('Topic name'), 'Joins'); await userEvent.click(screen.getByRole('button', { name: 'Add topic' }));
    expect(await screen.findByText('Topic added to your course.')).toBeInTheDocument(); expect(fetcher).toHaveBeenCalledWith(`/api/v1/teacher/courses/${id}/topics`, expect.objectContaining({ body: JSON.stringify({ title: 'Joins' }) }));
  });
  it('preserves a duplicate course title so the teacher can correct it', async () => {
    setup((path, opts) => path.endsWith('/courses') && opts.method === 'POST' ? json({ error: { code: 'DUPLICATE_COURSE' } }, 409) : undefined); await screen.findByText('Your first course starts here'); await userEvent.click(screen.getByRole('button', { name: 'Create course' })); await userEvent.type(screen.getByLabelText('Course title'), 'Existing'); await userEvent.click(screen.getByRole('button', { name: 'Save course' })); expect(await screen.findByRole('alert')).toHaveTextContent('already have a course'); expect(screen.getByLabelText('Course title')).toHaveValue('Existing');
  });
  it('returns to login when a feature request detects a revoked token', async () => {
    setup(path => path.endsWith('/dashboard') ? json({}, 401) : undefined); expect(await screen.findByText('Your session has ended. Please sign in again.')).toBeInTheDocument(); expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });
  it('revalidates roles after a denied feature request', async () => {
    setup(path => path.endsWith('/dashboard') ? json({}, 403) : path.endsWith('/me') ? json({ ...teacher, roles: ['student'] }) : undefined); expect(await screen.findByRole('heading', { name: 'This workspace is restricted' })).toBeInTheDocument(); expect(screen.queryByRole('link', { name: 'Teacher dashboard' })).not.toBeInTheDocument();
  });
  it('paginates the stored course list', async () => {
    const fetcher = setup(path => path.includes('/courses?') ? json({ ...page, total: 7, items: [course] }) : undefined); await screen.findByRole('button', { name: /Database Systems/ }); await userEvent.click(screen.getByRole('button', { name: 'Next' })); await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/v1/teacher/courses?offset=6&limit=6', expect.anything()));
  });
});

