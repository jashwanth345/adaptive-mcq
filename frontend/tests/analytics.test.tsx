import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { Analytics } from '../src/analytics/Analytics';
import { ApiError } from '../src/api';
const call = vi.fn(); let user = { roles: ['student'] }; const id = '11111111-1111-4111-8111-111111111111';
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call, user }) }));
const summary = { attempts: 0, students: 0, submitted: 0, expired: 0, in_progress: 0, overdue: 0, withheld: 0, scored_attempts: 0, average_score: null, average_elapsed_seconds: null, items: 0, excluded_items: 0, answered: 0, correct: 0, incorrect: 0, skipped: 0, accuracy: null };
const empty = { scope: 'student', assessment_id: null, assessment_title: null, generated_at: '2026-10-13T10:00:00Z', summary, breakdowns: [], missed_items: [], feedback: { reports: 0, issue_reporters: 0, open_issues: 0, helpful: 0, poor: 0 }, history: [], ranking_enabled: false, ranking: [] };
beforeEach(() => { call.mockReset(); user = { roles: ['student'] }; });
function mount(teacher = false, assessment = false) { return render(<MemoryRouter initialEntries={[assessment ? `/analytics/${id}` : '/analytics']}><Routes><Route path="/analytics/:assessmentId?" element={<Analytics teacher={teacher} />} /></Routes></MemoryRouter>); }
it('shows null metrics as no data and links recommendations without sample charts', async () => {
 call.mockResolvedValue(empty); mount(); expect(await screen.findByText('No attempts yet')).toBeVisible(); expect(screen.getAllByText('No data')).toHaveLength(2); expect(screen.queryByRole('progressbar')).not.toBeInTheDocument(); expect(screen.getByRole('link', { name: 'Recommendations & topic mastery' })).toHaveAttribute('href', '/learning');
});
it('keeps withheld history free of scores and elapsed times', async () => {
 call.mockResolvedValue({ ...empty, summary: { ...summary, attempts: 1, submitted: 1, withheld: 1 }, history: [{ id, assessment_id: id, title: 'Hidden results fixture', kind: 'classroom', state: 'submitted', started_at: '2026-10-13T10:00:00Z', attempt_number: 1, results_visible: false, score_percent: null, elapsed_seconds: null }] }); mount();
 expect(await screen.findByText('Withheld')).toBeVisible(); expect(screen.queryByText('0.0%')).not.toBeInTheDocument(); expect(screen.getByRole('link', { name: 'Hidden results fixture' })).toHaveAttribute('href', `/attempts/${id}`);
});
it('shows correct denominators including skip and exclusion counts', async () => {
 call.mockResolvedValue({ ...empty, summary: { ...summary, attempts: 2, submitted: 2, scored_attempts: 2, average_score: 50, accuracy: 100, answered: 1, correct: 1, skipped: 1, excluded_items: 1 }, breakdowns: [{ dimension: 'topic', key: id, label: 'DBMS fixture', items: 2, answered: 1, correct: 1, incorrect: 0, skipped: 1, accuracy: 100 }] }); mount();
 expect(await screen.findByText('1 correct / 1 answered approved items')).toBeVisible(); expect(screen.getByText('1 / 1 answered · 1 skipped · 2 items')).toBeVisible(); expect(screen.getByRole('progressbar')).toHaveAttribute('value', '100');
});
it('denies a student teacher analytics before requesting data', () => {
 mount(true); expect(screen.getByText('Teacher access required')).toBeVisible(); expect(call).not.toHaveBeenCalled();
});
it('keeps ranking off by default and enables it only within one owned assessment', async () => {
 user = { roles: ['teacher'] }; call.mockImplementation(async path => ({ ...empty, scope: 'teacher', assessment_id: id, assessment_title: 'Fixture assessment', ranking_enabled: path.includes('ranking=true'), ranking: path.includes('ranking=true') ? [{ rank: 1, display_name: 'Synthetic learner', score_percent: 75, attempt_id: id }] : [] })); mount(true, true);
 const toggle = await screen.findByRole('checkbox', { name: 'Show teacher-only ranking' }); expect(toggle).not.toBeChecked(); expect(screen.queryByText('Synthetic learner')).not.toBeInTheDocument(); await userEvent.click(toggle); expect(await screen.findByText('Synthetic learner')).toBeVisible(); expect(call.mock.calls[1][0]).toContain('ranking=true');
});
it('uses server pagination while retaining scope-wide counts', async () => {
 call.mockResolvedValue({ ...empty, summary: { ...summary, attempts: 21 } }); mount(); await userEvent.click(await screen.findByRole('button', { name: 'Next attempts' })); await waitFor(() => expect(call.mock.calls[1][0]).toBe('/student/analytics?offset=20&limit=20')); expect(await screen.findByText('21–21 of 21')).toBeVisible();
});
it('clears stale results when refreshing and permits retry on failure', async () => {
 call.mockResolvedValueOnce({ ...empty, summary: { ...summary, average_score: 75 } }).mockRejectedValueOnce(new ApiError(503, 'DATABASE_UNAVAILABLE')).mockResolvedValue(empty); mount(); await screen.findByText('75.0%'); await userEvent.click(screen.getByRole('button', { name: 'Refresh analytics' })); await screen.findByRole('alert'); expect(screen.queryByText('75.0%')).not.toBeInTheDocument(); await userEvent.click(screen.getByRole('button', { name: 'Refresh analytics' })); expect(await screen.findByText('No attempts yet')).toBeVisible();
});
it('links teacher question inspection and assessment filters', async () => {
 user = { roles: ['teacher'] }; call.mockResolvedValue({ ...empty, missed_items: [{ version_id: id, stem: 'Synthetic missed item', exposures: 3, students: 2, correct: 1, incorrect: 1, skipped: 1, missed_percent: 66.7 }] }); mount(true); const table = await screen.findByRole('region', { name: 'Question performance' }); expect(within(table).getByRole('link')).toHaveAttribute('href', `/teacher-review?version=${id}`); expect(within(table).getByText('66.7%')).toBeVisible(); expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
});
