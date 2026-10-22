import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import { ReviewPanel } from '../generator/ReviewPanel';
import { ValidationPanel } from '../generator/ValidationPanel';
import '../generator/generator.css';
import './review.css';

interface Summary { id: string; version: number; topic: string; stem: string; mode: string; state: string }
interface Draft { id: string; stem: string; options: string[]; correct_option: number; explanation: string; difficulty: string; cognitive_level: string; mode: string; evidence_quote: string; source: { title: string; page_start: number } }
interface Detail { draft: Draft; version: number; current: boolean; state: string; can_approve: boolean; blocker: string | null }
interface History { id: string; version: number; events: { action: string; note: string; created_at: string }[] }
interface Page<T> { items: T[]; total: number }

export function TeacherReview() {
  const { user } = useAuth();
  if (!user?.roles.includes('teacher')) return <section className="panel"><h1 tabIndex={-1}>Teacher access required</h1><p>Open your own workspace to continue.</p><Link to="/workspace">Go to workspace</Link></section>;
  return <ReviewWorkspace />;
}

function ReviewWorkspace() {
  const { authenticated } = useAuth(); const [params, setParams] = useSearchParams();
  const selected = params.get('version');
  const [queue, setQueue] = useState<Page<Summary> | null>(null); const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState<Detail | null>(null); const [history, setHistory] = useState<Page<History> | null>(null);
  const [historyOffset, setHistoryOffset] = useState(0); const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [saved, setSaved] = useState('');
  const pending = useRef<AbortController | null>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController(); setError(null);
    authenticated<Page<Summary>>(`/teacher/reviews?offset=${offset}&limit=6`, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setQueue(data); }).catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [authenticated, offset, revision]);
  useEffect(() => {
    const controller = new AbortController(); setDetail(null); setHistory(null); setError(null);
    if (selected && /^[a-f0-9-]{36}$/i.test(selected)) {
      void (async () => {
        const data = await authenticated<Detail>(`/teacher/reviews/${selected}`, { signal: controller.signal });
        const versions = await authenticated<Page<History>>(`/teacher/reviews/${selected}/versions?offset=${historyOffset}&limit=5`, { signal: controller.signal });
        if (!controller.signal.aborted) { setDetail(data); setHistory(versions); }
      })().catch(err => { if (!controller.signal.aborted) setError(err); });
    }
    return () => controller.abort();
  }, [authenticated, selected, revision, historyOffset]);
  function open(id: string) { if (busy) return; setSaved(''); setHistoryOffset(0); setParams({ version: id }); }
  async function change(body: Record<string, unknown>, action: 'edit' | 'approve' | 'reject') {
    if (busy || !detail) return;
    const path = `/teacher/reviews/${detail.draft.id}/${action === 'edit' ? 'edits' : 'decisions'}`;
    const payload = action === 'edit' ? body : { ...body, action };
    const fingerprint = JSON.stringify({ path, payload });
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setSaved('');
    try {
      const result = await authenticated<Detail>(path, { body: { ...payload, idempotency_key: retry.current.key }, signal: controller.signal });
      if (!controller.signal.aborted) {
        retry.current = null; setDetail(result); setHistoryOffset(0); setParams({ version: result.draft.id }); setRevision(n => n + 1);
        setSaved(action === 'edit' ? `Version ${result.version} saved. Fresh review and validation are required.` : action === 'approve' ? 'Teacher approval saved. No assessment has been published.' : 'Version rejected. Save a corrected version to reconsider it.');
      }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <>
    <div className="page-heading"><div><span className="eyebrow">Teacher quality control</span><h1 tabIndex={-1}>Review with confidence</h1><p>Inspect the evidence, refine the question and record your decision.</p></div><Badge tone="purple">Teacher review</Badge></div>
    <div className="draft-pipeline"><span><Icon name="layers" /> Inspect</span><span>→</span><span>Edit a new version</span><span>→</span><span>Run fresh checks</span><span>→</span><span><Icon name="shield" /> Approve</span></div>
    <ErrorNotice error={error} />{saved && <p className="notice success" role="status">{saved}</p>}
    <div className="teacher-review-grid"><aside className="panel"><div className="section-heading"><div><h2>Your review queue</h2><p>{queue?.total ?? 0} {queue?.total === 1 ? 'question' : 'questions'} · latest versions</p></div></div>
      <Link className="text-button" to="/drafts">Create another draft</Link>
      <button className="text-button" disabled={busy} onClick={() => setRevision(n => n + 1)}>Refresh review queue</button>
      {queue?.total === 0 && <p>Create a draft from your study materials to start reviewing.</p>}
      {queue?.items.map(item => <button className="draft-item" key={item.id} aria-pressed={selected === item.id} disabled={busy} onClick={() => open(item.id)}><strong>{item.topic}</strong><small>v{item.version}</small><span>{item.mode === 'mock' ? 'Test content' : 'AI origin'} · {item.state}</span></button>)}
      {queue && queue.total > 6 && <div className="review-actions"><button className="btn secondary" disabled={!offset || busy} onClick={() => setOffset(n => n - 6)}>Previous questions</button><button className="btn secondary" disabled={offset + 6 >= queue.total || busy} onClick={() => setOffset(n => n + 6)}>Next questions</button></div>}
    </aside><div>
      {!detail && <section className="panel material-empty"><Icon name="shield" size={38} /><h2>{selected ? 'Loading question…' : 'Your judgment matters'}</h2><p>Select a question to view its source, edit history and approval checks.</p></section>}
      {detail && <section className="panel teacher-review-detail" aria-label="Teacher question review">
        <div className="section-heading"><h2>Version {detail.version}</h2><Badge tone="purple">{detail.current ? detail.state : 'Superseded / archived'}</Badge></div>
        {detail.draft.mode === 'mock' && <p className="notice warning">Test content — no AI inference. Editing does not make this question eligible for approval.</p>}
        <h3 className="draft-stem">{detail.draft.stem}</h3><ol className="draft-options" type="A">{detail.draft.options.map((option, index) => <li key={index} className={index === detail.draft.correct_option ? 'proposed' : ''}>{option}{index === detail.draft.correct_option && <small>Proposed answer</small>}</li>)}</ol>
        <h3>Explanation</h3><p>{detail.draft.explanation}</p>
        <div className="draft-evidence"><span className="eyebrow">Original source · page {detail.draft.source.page_start}</span><h3>{detail.draft.source.title}</h3><blockquote>{detail.draft.evidence_quote}</blockquote><p>Source evidence stays attached to each edit. Fresh checks must establish whether it supports the revised question.</p></div>
        {detail.current && <EditForm key={detail.draft.id} draft={detail.draft} busy={busy} save={body => void change(body, 'edit')} />}
        {detail.current && detail.state === 'pending' && <ReviewPanel key={`ai-${detail.draft.id}`} versionId={detail.draft.id} draftMode={detail.draft.mode} />}
        {detail.current && detail.state !== 'rejected' && <ValidationPanel key={`checks-${detail.draft.id}`} versionId={detail.draft.id} />}
        <section className="draft-review" aria-label="Teacher decision"><h3>Record your decision</h3><p>Approval applies to this version and its saved evidence. Publication will recheck eligibility.</p>
          {detail.blocker && <p className="notice warning">{detail.blocker}</p>}
          <button className="text-button" disabled={busy} onClick={() => setRevision(n => n + 1)}>Refresh approval checks</button>
          {detail.current && <DecisionForm key={`${detail.draft.id}-${detail.state}`} busy={busy} ready={detail.can_approve} rejected={detail.state === 'rejected'} decide={(note, action) => void change({ note }, action)} />}
        </section>
        <section className="draft-review" aria-label="Version history"><h3>Version history</h3><p>Original content and decisions are preserved.</p>
          {history?.items.map(item => <div className="review-version" key={item.id}><button className="text-button" disabled={busy} onClick={() => open(item.id)}>View version {item.version}</button>{item.events.length === 0 && <p>Original generated draft</p>}{item.events.map((event, i) => <p key={i}><strong>{event.action}</strong> · {event.note}<small>{new Date(event.created_at).toLocaleString()}</small></p>)}</div>)}
          {history && history.total > 5 && <div className="review-actions"><button className="btn secondary" disabled={!historyOffset || busy} onClick={() => setHistoryOffset(n => n - 5)}>Newer versions</button><button className="btn secondary" disabled={historyOffset + 5 >= history.total || busy} onClick={() => setHistoryOffset(n => n + 5)}>Older versions</button></div>}
        </section>
      </section>}
    </div></div>
  </>;
}

function EditForm({ draft, busy, save }: { draft: Draft; busy: boolean; save: (body: Record<string, unknown>) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    save({ stem: String(form.get('stem')), explanation: String(form.get('explanation')), options: [0, 1, 2, 3].map(n => String(form.get(`option${n}`))), correct_option: Number(form.get('answer')), difficulty: String(form.get('difficulty')), cognitive_level: String(form.get('cognitive')), note: String(form.get('note')) });
  }
  return <details className="review-editor"><summary>Edit as a new version</summary><p>The original stays unchanged. New versions start without approval or validation.</p>
    <form aria-label="Edit question version" onSubmit={submit}><fieldset disabled={busy}>
      <label className="field">Question<textarea aria-label="Question" name="stem" defaultValue={draft.stem} minLength={10} maxLength={350} required rows={3} /></label>
      {draft.options.map((option, n) => <label className="field" key={n}>Option {String.fromCharCode(65 + n)}<input name={`option${n}`} defaultValue={option} maxLength={150} required /></label>)}
      <label className="field">Correct answer<select name="answer" defaultValue={draft.correct_option}>{[0, 1, 2, 3].map(n => <option key={n} value={n}>{String.fromCharCode(65 + n)}</option>)}</select></label>
      <label className="field">Explanation<textarea aria-label="Explanation" name="explanation" defaultValue={draft.explanation} required minLength={10} maxLength={600} rows={3} /></label>
      <div className="draft-settings"><label className="field">Difficulty<select name="difficulty" defaultValue={draft.difficulty}>{['easy', 'medium', 'hard'].map(s => <option key={s}>{s}</option>)}</select></label><label className="field">Cognitive level<select name="cognitive" defaultValue={draft.cognitive_level}>{['remember', 'understand'].map(s => <option key={s}>{s}</option>)}</select></label></div>
      <label className="field">Reason for this edit<textarea aria-label="Reason for this edit" name="note" required minLength={3} maxLength={600} rows={2} /></label>
      <button className="btn primary" aria-busy={busy}>Save new version</button>
    </fieldset></form>
  </details>;
}

function DecisionForm({ busy, ready, rejected, decide }: { busy: boolean; ready: boolean; rejected: boolean; decide: (note: string, action: 'approve' | 'reject') => void }) {
  const [note, setNote] = useState(''); const [confirm, setConfirm] = useState<'approve' | 'reject' | null>(null);
  return <div><label className="field">Teacher review note<textarea value={note} onChange={event => { setNote(event.target.value); setConfirm(null); }} disabled={busy || rejected} maxLength={600} rows={2} /></label>
    {!confirm ? <div className="review-actions"><button className="btn primary" disabled={busy || !ready || note.trim().length < 3} onClick={() => setConfirm('approve')}>Approve this version</button><button className="btn secondary" disabled={busy || rejected || note.trim().length < 3} onClick={() => setConfirm('reject')}>Reject this version</button></div> : <div className="notice warning"><p>{confirm === 'approve' ? 'Confirm that you reviewed the question, options, explanation and source. Approval does not publish an assessment.' : 'Reject this version? A corrected new version will be required before approval.'}</p><div className="review-actions"><button className="btn primary" disabled={busy} onClick={() => decide(note.trim(), confirm)}>Confirm {confirm === 'approve' ? 'approval' : 'rejection'}</button><button className="btn secondary" disabled={busy} onClick={() => setConfirm(null)}>Cancel decision</button></div></div>}
  </div>;
}
