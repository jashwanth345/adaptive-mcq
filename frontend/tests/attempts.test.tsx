import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { Attempt, type AttemptData } from '../src/attempts/Attempt';
import { Learning } from '../src/attempts/Learning';
import { ApiError } from '../src/api';

const call = vi.fn(); let roles = ['student'];
vi.mock('../src/auth', () => ({ useAuth: () => ({ authenticated: call, user: { roles } }) }));
const id = '11111111-1111-4111-8111-111111111111';
const base: AttemptData = { id, assessment_id: id, title: 'Synthetic assessment', kind: 'classroom', state: 'in_progress', revision: 1, server_now: new Date().toISOString(), started_at: new Date().toISOString(), release_policy: 'after_submit', results_released: false, items: [{ position: 1, version_id: id, stem: 'Which process reduces redundancy?', options: ['Normalization', 'Replication', 'Sorting', 'Indexing'], flagged: false, under_review: false }] };
let current = structuredClone(base);
const learning = { policy: { version: 'bounded-performance-v1', minimum_evidence: 3, decay: .95, promote_at: .75, demote_at: .4, recent_window: 3, weights: [1, 2, 3] }, topics: [], eligible_observations: 0, retained_evidence_count: 0, recommendation: null, scope: 'Test fixture policy' };
beforeEach(() => { call.mockClear(); current = structuredClone(base); roles = ['student']; call.mockImplementation(async () => current); });
function mount(profile = false) { return render(<MemoryRouter initialEntries={[`/attempts/${id}`]}><Routes><Route path="/attempts/:attemptId" element={profile ? <Learning /> : <Attempt />} /></Routes></MemoryRouter>); }

it('saves choices and flags before enabling explicit submission', async () => {
  call.mockImplementation(async (_path, options) => { if (options?.body?.answers) current = { ...current, revision: 2, items: current.items.map((item, i) => ({ ...item, ...options.body.answers[i] })) }; return current; });
  mount(); await screen.findByText('Which process reduces redundancy?');
  expect(screen.queryByText(/Correct answer:/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('radio', { name: /Normalization/ }));
  await userEvent.click(screen.getByRole('checkbox', { name: 'Flag for review' }));
  expect(screen.getByRole('button', { name: 'Submit assessment' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Save progress' }));
  expect(await screen.findByText('Progress saved on this computer.')).toBeInTheDocument();
  expect(call).toHaveBeenCalledWith(`/student/attempts/${id}/save`, expect.objectContaining({ body: expect.objectContaining({ revision: 1, answers: [{ position: 1, selected_option: 0, flagged: true }] }) }));
  await userEvent.click(screen.getByRole('button', { name: 'Submit assessment' }));
  expect(screen.getByRole('button', { name: 'Confirm submission' })).toBeInTheDocument();
});

it('retains unsaved answers and retry key when saving fails', async () => {
  const keys: string[] = []; call.mockImplementation(async (_path, options) => { if (options?.body) { keys.push(options.body.idempotency_key); throw new ApiError(503, 'DATABASE_UNAVAILABLE'); } return current; });
  mount(); await userEvent.click(await screen.findByRole('radio', { name: /Normalization/ }));
  await userEvent.click(screen.getByRole('button', { name: 'Save progress' })); await screen.findByRole('alert');
  expect(screen.getByRole('radio', { name: /Normalization/ })).toBeChecked();
  await userEvent.click(screen.getByRole('button', { name: 'Save progress' }));
  await waitFor(() => expect(keys).toHaveLength(2)); expect(keys[0]).toBe(keys[1]);
});

it('withholds results and solutions during the teacher embargo', async () => {
  current.state = 'submitted'; current.release_policy = 'after_close'; mount();
  expect(await screen.findByText(/Scores and solutions will be released/)).toBeInTheDocument();
  expect(screen.queryByText(/Correct answer:/)).not.toBeInTheDocument(); expect(screen.queryByText(/Points from/)).not.toBeInTheDocument();
});

it('clears a previous reload success notice when the next reload fails', async () => {
  let calls = 0;
  call.mockImplementation(async () => { if (++calls === 3) throw new ApiError(503, 'DATABASE_UNAVAILABLE'); return current; });
  mount(); await screen.findByText('Which process reduces redundancy?');
  await userEvent.click(screen.getByRole('button', { name: 'Reload saved attempt' }));
  expect(await screen.findByText('Saved attempt loaded.')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Reload saved attempt' }));
  await screen.findByRole('alert');
  expect(screen.queryByText('Saved attempt loaded.')).not.toBeInTheDocument();
  expect(screen.getByText('Which process reduces redundancy?')).toBeVisible();
});

it('renders released stored scores and mapped solutions', async () => {
  current = { ...current, state: 'submitted', results_released: true, result: { awarded_points: 1, possible_points: 1, item_count: 1 }, items: [{ ...current.items[0], selected_option: 0, correct_option: 0, is_correct: true, explanation: 'Normalization reduces redundancy.', source_quotes: ['Synthetic source evidence.'] }] };
  mount(); expect(await screen.findByText('1 / 1')).toBeInTheDocument(); expect(screen.getByText('Correct answer: A. Normalization')).toBeInTheDocument();
});

it('asks the server to finalize an expired attempt and disables answers', async () => {
  let calls = 0; current.deadline = new Date(Date.now() - 10000).toISOString();
  call.mockImplementation(async () => ++calls === 1 ? current : { ...current, state: 'expired', results_released: true, result: { awarded_points: 0, possible_points: 1, item_count: 1 } });
  mount(); expect(await screen.findByRole('heading', { name: 'Time limit reached' })).toBeInTheDocument(); expect(calls).toBe(2);
});

it('shows an honest empty learning profile and no unsafe practice action', async () => {
  call.mockResolvedValue(learning); mount(true);
  expect(await screen.findByRole('heading', { name: 'Insufficient evidence' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Start suggested practice' })).not.toBeInTheDocument();
  expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
});

it('shows covered-level estimates as provisional and exposes policy assumptions', async () => {
  call.mockResolvedValue({ ...learning, eligible_observations: 3, topics: [{ topic_id: id, topic: 'DBMS', observations: 3, performance_index: 79.4, recommended_difficulty: 'medium', reason: 'Three synthetic correct responses.', levels: [{ difficulty: 'easy', observations: 3, covered: true }] }] });
  mount(true); expect(await screen.findByText('79.4%')).toBeInTheDocument(); expect(screen.getByText('medium next')).toBeInTheDocument();
  await userEvent.click(screen.getByText('Policy assumptions — to be evaluated')); expect(screen.getByText(/bounded-performance-v1:/)).toBeVisible();
});

it('blocks non-student access without issuing a request', () => { roles = ['teacher']; mount(); expect(screen.getByText('Student access required')).toBeInTheDocument(); expect(call).not.toHaveBeenCalled(); });
