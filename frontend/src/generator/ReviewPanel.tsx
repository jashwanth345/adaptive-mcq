import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../api';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';

interface Readiness { mode: 'mock' | 'disabled' | 'ollama'; ready: boolean; configured_same_model: boolean; error_code: string | null }
interface Check { name: string; outcome: 'pass' | 'fail' | 'acceptable' | 'issue' | 'uncertain' | 'not_evaluated'; detail: string }
export interface Review { id: string; mode: 'mock' | 'ollama'; recommendation: 'NOT_EVALUATED' | 'PASS' | 'REGENERATE' | 'REJECT'; publication_eligible: false; checks: Check[]; reason: string; ai_executed: boolean; blind_option: number | null; model_relationship: string; pending: string[]; created_at: string }
interface History { items: Review[]; total: number }
const outcome = { pass: 'Passed check', fail: 'Failed check', acceptable: 'Model: acceptable', issue: 'Model: issue', uncertain: 'Model: uncertain', not_evaluated: 'Not evaluated' };

export function ReviewPanel({ versionId, draftMode }: { versionId: string; draftMode: string }) {
  const { authenticated } = useAuth();
  const [status, setStatus] = useState<Readiness | null>(null); const [history, setHistory] = useState<History | null>(null);
  const [selected, setSelected] = useState<Review | null>(null); const [offset, setOffset] = useState(0); const [revision, setRevision] = useState(0);
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const key = useRef<string | null>(null); const pending = useRef<AbortController | null>(null);
  const path = `/verifier/drafts/${versionId}/reports`;
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController(); setError(null);
    Promise.all([
      authenticated<Readiness>('/verifier/status', { signal: controller.signal }),
      authenticated<History>(`${path}?offset=${offset}&limit=3`, { signal: controller.signal }),
    ]).then(([state, saved]) => {
      if (!controller.signal.aborted) { setStatus(state); setHistory(saved); setSelected(saved.items[0] ?? null); }
    }).catch(err => { if (!controller.signal.aborted) { setStatus(null); setError(err); } });
    return () => controller.abort();
  }, [authenticated, path, offset, revision]);
  async function run() {
    if (busy || !status?.ready) return;
    const controller = new AbortController(); pending.current = controller; key.current ??= crypto.randomUUID();
    setBusy(true); setError(null);
    try {
      const report = await authenticated<Review>(path, { body: { idempotency_key: key.current }, signal: controller.signal });
      if (!controller.signal.aborted) { key.current = null; setSelected(report); setOffset(0); setRevision(n => n + 1); }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const excluded = status?.mode === 'ollama' && draftMode === 'mock';
  return <section className="draft-review" aria-label="Advisory draft review">
    <div className="section-heading"><div><span className="eyebrow">Review before release</span><h2>Verification workspace</h2></div><Icon name="shield" size={25} /></div>
    <p>Reports belong to this saved draft. A report never approves or publishes a question.</p>
    {status?.mode === 'mock' && <p className="notice warning"><strong>Test review — no AI verification</strong><br />Checks the question format and recorded source evidence. Answer correctness and educational quality remain not evaluated.</p>}
    {status?.mode === 'disabled' && <p className="notice warning">New reviews are disabled. Saved reports remain available.</p>}
    {excluded && <p className="notice warning">This is a test-generated draft. Real AI review is unavailable for test content.</p>}
    {status?.mode === 'ollama' && !excluded && <p className="notice warning">The local model will answer without seeing the proposed key, then review the answer and explanation. Its recommendation is advisory.{status.configured_same_model && ' Both roles currently use the same checkpoint; this is not independent-model verification.'}</p>}
    <ErrorNotice error={error} />{status?.error_code && <ErrorNotice error={new ApiError(503, status.error_code)} />}
    {!status && !error && <p role="status">Loading review readiness and history…</p>}
    <div className="review-actions"><button className="btn secondary" disabled={busy || !status?.ready || excluded} onClick={() => void run()}>{busy ? 'Reviewing draft…' : status?.mode === 'mock' ? 'Run test review' : 'Run local AI review'}</button><button className="text-button" disabled={busy} onClick={() => setRevision(n => n + 1)}>Refresh reviews</button></div>
    {busy && <p role="status">Keep this page open. A completed report is saved privately; the draft remains unapproved.</p>}
    {history?.total === 0 && <p>No saved review reports yet.</p>}
    {!!history?.total && <div className="review-history"><h3>Saved review reports</h3>{history.items.map((report, index) => <button className="text-button" aria-pressed={selected?.id === report.id} key={report.id} onClick={() => setSelected(report)} disabled={busy}>Open {report.mode === 'mock' ? 'test' : 'AI'} report {history.total - offset - index}</button>)}{history.total > 3 && <div className="material-pagination"><button className="btn secondary" disabled={!offset || busy} onClick={() => setOffset(n => n - 3)}>Newer reports</button><button className="btn secondary" disabled={offset + 3 >= history.total || busy} onClick={() => setOffset(n => n + 3)}>Older reports</button></div>}</div>}
    {selected && <article className="review-result" aria-label="Saved review result"><Badge tone="purple">{selected.mode === 'mock' ? 'Test report · AI quality not evaluated' : `AI recommendation: ${selected.recommendation}`}</Badge><p className="review-reason">{selected.reason}</p><p><strong>Publication status: not approved</strong></p>
      <ul className="review-checks">{selected.checks.map(check => <li key={check.name}><div><strong>{check.name}</strong><span>{outcome[check.outcome]}</span></div><p>{check.detail}</p></li>)}</ul>
      {selected.ai_executed && <p>Blind answer: {selected.blind_option === null ? 'No unique answer identified' : String.fromCharCode(65 + selected.blind_option)}. {selected.model_relationship === 'same_checkpoint' ? 'Same model checkpoint used in both roles; independent-model verification is not established.' : 'Different checkpoint recorded; statistical independence and quality still require evaluation.'}</p>}
      <details><summary>Remaining checks</summary><ul>{selected.pending.map(item => <li key={item}>{item}</li>)}</ul></details>
    </article>}
  </section>;
}
