import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '../auth';
import { Badge, ErrorNotice } from '../ui';

interface MathResult { status: string; computed: string | null; matching_options: number[]; detail: string }
export interface ValidationReport { id: string; technical_pass: boolean; publication_eligible: false; blockers: string[]; math: MathResult; duplicates: { status: string; complete: boolean; scanned: number; match_count: number; matches: { version_id: string; kind: string; similarity: number }[]; detail: string }; checks: { name: string; outcome: string; detail: string }[]; created_at: string }
interface History { items: ValidationReport[]; total: number }

export function ValidationPanel({ versionId }: { versionId: string }) {
  const { authenticated } = useAuth();
  const [history, setHistory] = useState<History | null>(null); const [selected, setSelected] = useState<ValidationReport | null>(null);
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false); const [offset, setOffset] = useState(0); const [revision, setRevision] = useState(0);
  const key = useRef<string | null>(null); const pending = useRef<AbortController | null>(null);
  const path = `/validation/drafts/${versionId}/reports`;
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController(); setError(null);
    authenticated<History>(`${path}?offset=${offset}&limit=3`, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) { setHistory(data); setSelected(data.items[0] ?? null); }
    }).catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [authenticated, path, offset, revision]);
  async function run() {
    if (busy) return;
    const controller = new AbortController(); pending.current = controller; key.current ??= crypto.randomUUID(); setBusy(true); setError(null);
    try {
      const report = await authenticated<ValidationReport>(path, { body: { idempotency_key: key.current }, signal: controller.signal });
      if (!controller.signal.aborted) { key.current = null; setSelected(report); setOffset(0); setRevision(n => n + 1); }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="draft-review draft-validation" aria-label="Draft validation">
    <span className="eyebrow">Checks before release</span><h2>Validation workspace</h2>
    <p>Check source integrity, mathematical answerability and repeated questions. Test content remains blocked from release.</p>
    <ErrorNotice error={error} />
    <div className="review-actions"><button className="btn secondary" disabled={busy} onClick={() => void run()}>{busy ? 'Checking draft…' : 'Run validation'}</button><button className="text-button" disabled={busy} onClick={() => setRevision(n => n + 1)}>Refresh validation</button></div>
    {!history && !error && <p role="status">Loading validation history…</p>}
    {history?.total === 0 && <p>No saved validation reports yet.</p>}
    {!!history?.total && <div className="review-history"><h3>Saved validation reports</h3>{history.items.map((report, i) => <button className="text-button" key={report.id} disabled={busy} aria-pressed={selected?.id === report.id} onClick={() => setSelected(report)}>Open validation {history.total - offset - i}</button>)}{history.total > 3 && <div className="material-pagination"><button className="btn secondary" disabled={!offset || busy} onClick={() => setOffset(n => n - 3)}>Newer validations</button><button className="btn secondary" disabled={offset + 3 >= history.total || busy} onClick={() => setOffset(n => n + 3)}>Older validations</button></div>}</div>}
    {selected && <article className="review-result" aria-label="Saved validation result"><Badge tone="purple">{selected.technical_pass ? 'Technical checks passed · not approved' : 'Release blocked'}</Badge>
      <p>Saved snapshot: {new Date(selected.created_at).toLocaleString()}. Run again after new drafts or reviews; release rechecks freshness.</p>
      <p><strong>This report does not approve or publish the question.</strong></p>
      {!!selected.blockers.length && <ul className="validation-blockers">{selected.blockers.map(reason => <li key={reason}>{reason}</li>)}</ul>}
      <ul className="review-checks">{selected.checks.map(check => <li key={check.name}><div><strong>{check.name}</strong><span>{check.outcome === 'pass' ? 'Passed check' : 'Failed check'}</span></div><p>{check.detail}</p></li>)}
        <li><div><strong>Duplicate check</strong><span>{selected.duplicates.status}</span></div><p>{selected.duplicates.scanned} other questions checked · {selected.duplicates.match_count} candidate matches.</p><p>{selected.duplicates.detail}</p>{selected.duplicates.matches.map(match => <p key={match.version_id}>{match.kind === 'exact' ? 'Exact normalized match' : 'Similar wording'} · <code>{match.version_id.slice(0, 8)}</code></p>)}</li>
        <li><div><strong>Mathematical check</strong><span>{selected.math.status.replaceAll('_', ' ')}</span></div><p>{selected.math.detail}</p>{selected.math.computed !== null && <p>Exact result: {selected.math.computed}</p>}</li>
      </ul>
      <p>Classroom release requires teacher approval. Private-practice release is a separate planned workflow. Factual quality, missed paraphrases and model hardware still need evaluation.</p>
    </article>}
    <MathPreview />
  </section>;
}

export function MathPreview() {
  const { authenticated } = useAuth(); const [stem, setStem] = useState(''); const [options, setOptions] = useState(['', '', '', '']); const [answer, setAnswer] = useState(0);
  const [result, setResult] = useState<MathResult | null>(null); const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false); const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setResult(null);
    try {
      const data = await authenticated<{ result: MathResult }>('/validation/math-check', { body: { stem, options, correct_option: answer }, signal: controller.signal });
      if (!controller.signal.aborted) setResult(data.result);
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const clear = () => { setResult(null); setError(null); };
  return <details className="math-preview"><summary>Try the arithmetic checker</summary>
    <p>Unsaved preview only. This does not change your draft or provide release evidence. Supports exact numbers, parentheses and + − * / **. Word problems, units, symbolic algebra and rounding are unsupported.</p>
    <button className="text-button" disabled={busy} onClick={() => { clear(); setStem('Calculate: (3 + 5) / 2'); setOptions(['4', '3', '5', '8']); setAnswer(0); }}>Load arithmetic example</button>
    <form aria-label="Arithmetic preview" onSubmit={event => void submit(event)}>
      <label className="field">Math question<input required maxLength={350} value={stem} placeholder="Calculate: (3 + 5) / 2" disabled={busy} onChange={e => { clear(); setStem(e.target.value); }} /></label>
      <div className="draft-settings">{options.map((option, i) => <label className="field" key={i}>Math option {String.fromCharCode(65 + i)}<input required maxLength={128} value={option} disabled={busy} onChange={e => { clear(); setOptions(values => values.map((value, n) => n === i ? e.target.value : value)); }} /></label>)}</div>
      <label className="field">Proposed math answer<select value={answer} disabled={busy} onChange={e => { clear(); setAnswer(Number(e.target.value)); }}>{['A', 'B', 'C', 'D'].map((label, i) => <option key={label} value={i}>{label}</option>)}</select></label>
      <ErrorNotice error={error} /><button className="btn secondary" disabled={busy}>{busy ? 'Calculating…' : 'Check arithmetic'}</button>
    </form>
    {result && <div className="review-result" role="status"><strong>Arithmetic preview: {result.status}</strong><p>{result.detail}</p>{result.computed !== null && <p>Exact result: {result.computed}</p>}<p>Not saved · no release eligibility</p></div>}
  </details>;
}
