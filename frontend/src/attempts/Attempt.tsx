import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import './attempts.css';
import { ReportForm } from '../feedback/Feedback';

export interface Item { position: number; version_id: string; stem: string; options: string[]; selected_option?: number | null; flagged: boolean; under_review: boolean; correct_option?: number; explanation?: string; is_correct?: boolean; source_quotes?: string[] }
export interface AttemptData { id: string; assessment_id: string; title: string; kind: string; state: string; revision: number; deadline?: string; server_now: string; started_at: string; submitted_at?: string; results_released: boolean; release_policy: string; items: Item[]; result?: { awarded_points: number; possible_points: number; item_count: number } }

export function Attempt() {
  const { user } = useAuth();
  if (!user?.roles.includes('student')) return <section className="panel"><h1 tabIndex={-1}>Student access required</h1><Link to="/workspace">Go to workspace</Link></section>;
  return <AttemptPlayer />;
}

function AttemptPlayer() {
  const { attemptId } = useParams(); const { authenticated } = useAuth();
  const [data, setData] = useState<AttemptData | null>(null); const [items, setItems] = useState<Item[]>([]); const [index, setIndex] = useState(0);
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false); const [notice, setNotice] = useState(''); const [confirm, setConfirm] = useState(false);
  const [tick, setTick] = useState(Date.now()); const [serverOffset, setServerOffset] = useState(0);
  const pending = useRef<AbortController | null>(null); const retry = useRef<{ fingerprint: string; key: string } | null>(null); const expirationChecked = useRef(false);
  const dirty = data?.state === 'in_progress' && JSON.stringify(items.map(x => [x.selected_option ?? null, x.flagged])) !== JSON.stringify(data.items.map(x => [x.selected_option ?? null, x.flagged]));
  const remaining = data?.deadline ? Math.max(0, Math.ceil((Date.parse(data.deadline) - tick - serverOffset) / 1000)) : null;
  const timedOut = remaining === 0 && data?.state === 'in_progress';
  function accept(value: AttemptData) { setData(value); setItems(value.items); setServerOffset(Date.parse(value.server_now) - Date.now()); setTick(Date.now()); setIndex(i => Math.min(i, value.items.length - 1)); }
  useEffect(() => { const timer = setInterval(() => setTick(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    const controller = new AbortController(); pending.current = controller; setData(null); setError(null); expirationChecked.current = false;
    authenticated<AttemptData>(`/student/attempts/${attemptId}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) accept(value); }).catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [authenticated, attemptId]);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    function unload(event: BeforeUnloadEvent) { if (dirty) { event.preventDefault(); event.returnValue = ''; } }
    function leave(event: MouseEvent) { if (dirty && (event.target as HTMLElement).closest('a[href]') && !window.confirm('Leave with unsaved answers? Save your progress first to keep these changes.')) { event.preventDefault(); event.stopPropagation(); } }
    window.addEventListener('beforeunload', unload); document.addEventListener('click', leave, true);
    return () => { window.removeEventListener('beforeunload', unload); document.removeEventListener('click', leave, true); };
  }, [dirty]);
  async function reload() {
    if (busy || dirty && !window.confirm('Reload the saved attempt and discard your unsaved changes?')) return;
    const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setNotice('');
    try { const value = await authenticated<AttemptData>(`/student/attempts/${attemptId}`, { signal: controller.signal }); if (!controller.signal.aborted) { accept(value); setNotice('Saved attempt loaded.'); } }
    catch (err) { if (!controller.signal.aborted) { setError(err); expirationChecked.current = false; } } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  useEffect(() => {
    if (!timedOut || busy || expirationChecked.current) return;
    expirationChecked.current = true;
    const controller = new AbortController(); pending.current = controller; setBusy(true);
    authenticated<AttemptData>(`/student/attempts/${attemptId}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) { accept(value); setNotice('The server finalized your saved answers at the time limit.'); } }).catch(err => { if (!controller.signal.aborted) setError(err); }).finally(() => { if (!controller.signal.aborted) setBusy(false); });
  }, [timedOut, busy, authenticated, attemptId]);
  async function change(action: 'save' | 'submit') {
    if (busy || !data) return; setBusy(true); setError(null); setNotice('');
    const controller = new AbortController(); pending.current = controller;
    const body = { revision: data.revision, ...(action === 'save' ? { answers: items.map(item => ({ position: item.position, selected_option: item.selected_option ?? null, flagged: item.flagged })) } : {}) };
    const fingerprint = JSON.stringify({ id: data.id, action, body });
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    try { const value = await authenticated<AttemptData>(`/student/attempts/${data.id}/${action}`, { body: { ...body, idempotency_key: retry.current.key }, signal: controller.signal }); if (!controller.signal.aborted) { accept(value); retry.current = null; setConfirm(false); setNotice(value.state === 'expired' ? 'Time expired. Only previously saved answers were graded.' : action === 'save' ? 'Progress saved on this computer.' : 'Submission recorded.'); } }
    catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const current = items[index]; const answered = items.filter(item => item.selected_option != null).length;
  function update(values: Partial<Item>) { setItems(old => old.map((item, n) => n === index ? { ...item, ...values } : item)); setConfirm(false); setNotice(''); }
  return <><div className="page-heading"><div><span className="eyebrow">{data?.kind === 'practice' ? 'Private practice · automatically checked' : 'Classroom assessment'}</span><h1 tabIndex={-1}>{data?.title ?? 'Your attempt'}</h1><p>Saved question versions and option order stay the same when you resume.</p></div><Badge tone="purple">{data?.state ?? 'Loading'}</Badge></div>
    <ErrorNotice error={error} />{notice && <p role="status" className="notice success">{notice}</p>}
    <div className="attempt-toolbar"><Link to="/workspace/student">Attempt history</Link><Link to="/learning">My learning</Link><button className="text-button" disabled={busy} onClick={() => void reload()}>Reload saved attempt</button>{data?.state === 'in_progress' && <strong role="timer">{remaining == null ? 'Untimed' : `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')} remaining`}</strong>}</div>
    {!data && !error && <p role="status">Loading your saved attempt…</p>}
    {data?.state === 'in_progress' && current && <div className="attempt-grid"><aside className="panel"><h2>Your progress</h2><p>{answered} of {items.length} answered</p><progress max={items.length} value={answered} aria-label="Answered questions" /><div className="question-nav">{items.map((item, n) => <button key={item.position} aria-label={`Question ${n + 1}${item.flagged ? ', flagged' : ''}`} aria-current={n === index ? 'step' : undefined} className={item.selected_option != null ? 'answered' : ''} disabled={busy} onClick={() => setIndex(n)}>{n + 1}{item.flagged && <span aria-hidden="true"> *</span>}</button>)}</div><p>{dirty ? 'Unsaved changes — save before leaving.' : 'All displayed progress is saved.'}</p><button className="btn primary" disabled={busy || !dirty || timedOut} onClick={() => void change('save')}>Save progress</button></aside>
      <section className="panel"><span className="eyebrow">Question {index + 1} of {items.length}</span><h2 className="attempt-stem">{current.stem}</h2>{current.under_review && <p className="notice warning">This item is under review. Your original attempt record will be preserved.</p>}
        <fieldset disabled={busy || timedOut}><legend className="sr-only">Choose one answer</legend><div className="attempt-options">{current.options.map((option, i) => <label key={i} className={current.selected_option === i ? 'selected' : ''}><input type="radio" name={`question-${current.position}`} checked={current.selected_option === i} onChange={() => update({ selected_option: i })} /><span className="option-letter">{String.fromCharCode(65 + i)}</span><span>{option}</span></label>)}</div><div className="attempt-toolbar"><button type="button" className="text-button" onClick={() => update({ selected_option: null })}>Clear answer</button><label><input type="checkbox" checked={current.flagged} onChange={event => update({ flagged: event.target.checked })} /> Flag for review</label></div></fieldset>
        <div className="attempt-toolbar"><button className="btn secondary" disabled={index === 0 || busy} onClick={() => setIndex(n => n - 1)}>Previous</button><button className="btn secondary" disabled={index === items.length - 1 || busy} onClick={() => setIndex(n => n + 1)}>Next</button></div>
        <div className="attempt-submit"><p>Unanswered questions receive zero points. Save your choices before submitting.</p><button className="btn primary" disabled={busy || dirty || timedOut} onClick={() => setConfirm(true)}>Submit assessment</button>{confirm && <div className="notice warning" role="group" aria-label="Confirm submission"><p>Submit your saved answers? {items.length - answered} questions are unanswered. Submission cannot be edited.</p><button className="btn secondary" disabled={busy} onClick={() => setConfirm(false)}>Keep reviewing</button><button className="btn primary" disabled={busy || dirty || timedOut} onClick={() => void change('submit')}>Confirm submission</button></div>}</div>
      </section></div>}
    {data && data.state !== 'in_progress' && <section className="panel"><div className="section-heading"><h2>{data.state === 'expired' ? 'Time limit reached' : 'Attempt submitted'}</h2><Icon name="shield" /></div>
      {!data.results_released ? <p className="notice warning">Your answers are saved. Scores and solutions will be released after your teacher closes the assessment.</p> : <><div className="attempt-score"><strong>{data.result?.awarded_points} / {data.result?.possible_points}</strong><span>Points from your recorded answers</span></div>{items.some(i => i.under_review) && <p className="notice warning">Some questions are under review. The preserved score uses the original answer key; these items do not contribute to your learning profile.</p>}
        {items.map(item => <article key={item.position} className="attempt-result"><h3>{item.position}. {item.stem}</h3><p>Your answer: {item.selected_option == null ? 'Skipped' : `${String.fromCharCode(65 + item.selected_option)}. ${item.options[item.selected_option]}`}</p>{item.correct_option != null && <><p><strong>Correct answer: {String.fromCharCode(65 + item.correct_option)}. {item.options[item.correct_option]}</strong></p><p>{item.explanation}</p><details><summary>Supporting source excerpts</summary>{item.source_quotes?.map((quote, n) => <blockquote key={n}>{quote}</blockquote>)}</details></>}{item.under_review && <p>Solution withheld while this item is under review.</p>}</article>)}
      </>}<Link className="btn primary" to="/learning">View topic progress and next practice</Link><section aria-label="Question feedback"><h2>Help improve these questions</h2><p>Report issues or rate each question after your attempt. Scores remain unchanged while reports are reviewed.</p>{items.map(item => <ReportForm key={item.version_id} attemptId={data.id} versionId={item.version_id} number={item.position} />)}<Link to="/feedback">View my feedback history</Link></section></section>}
  </>;
}
