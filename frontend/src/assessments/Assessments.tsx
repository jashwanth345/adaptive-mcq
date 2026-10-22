import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import './assessments.css';

interface Page<T> { items: T[]; total: number }
interface Summary { id: string; title: string; state: string; question_count: number }
interface Settings { time_limit_seconds: number | null; max_attempts: number; randomize_questions: boolean; randomize_options: boolean; release_policy: string }
interface Detail extends Summary, Settings { revision: number; course_id: string; can_publish: boolean; issued_code: string | null; questions: { version_id: string; position: number; version: number; stem: string; state: string; mode: string }[]; participants: { student_id: string; email: string; display_name: string; active: boolean }[]; codes: { id: string; expires_at: string; revoked_at: string | null; active: boolean }[] }
interface Candidate { id: string; version: number; stem: string; state: string; mode: string }
interface Admission extends Settings { id: string; title: string; question_count: number; available: boolean }
const root = '/teacher/assessments';
const date = (value: string) => new Date(value).toLocaleString();

export function TeacherAssessments() {
  const { user } = useAuth();
  if (!user?.roles.includes('teacher')) return <section className="panel"><h1 tabIndex={-1}>Teacher access required</h1><Link to="/workspace">Go to workspace</Link></section>;
  return <TeacherWorkspace />;
}

function TeacherWorkspace() {
  const { authenticated } = useAuth();
  const [page, setPage] = useState<Page<Summary> | null>(null); const [offset, setOffset] = useState(0); const [refresh, setRefresh] = useState(0);
  const [detail, setDetail] = useState<Detail | null>(null); const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState('');
  const pending = useRef<AbortController | null>(null); const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    authenticated<Page<Summary>>(`${root}?offset=${offset}&limit=6`, { signal: controller.signal }).then(data => { if (!controller.signal.aborted) setPage(data); }).catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [authenticated, offset, refresh]);
  async function open(id: string) {
    if (busy) return; const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setNotice(''); setDetail(null); setCreating(false);
    try { const result = await authenticated<Detail>(`${root}/${id}`, { signal: controller.signal }); if (!controller.signal.aborted) setDetail(result); }
    catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function change(action: string, body: Record<string, unknown>) {
    if (busy || action !== 'create' && !detail) return;
    const path = action === 'create' ? root : `${root}/${detail!.id}/${action}`;
    const fingerprint = JSON.stringify({ path, body });
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setNotice('');
    try {
      const result = await authenticated<Detail>(path, { body: { ...body, idempotency_key: retry.current.key }, signal: controller.signal });
      if (!controller.signal.aborted) { setDetail(result); setCreating(false); setRefresh(n => n + 1); retry.current = null; setNotice(action === 'publish' ? 'Assessment published. Share the reference code with permitted students.' : action === 'rotate' ? 'New code created. Earlier codes no longer grant access.' : action === 'revoke' ? 'Reference codes revoked. New access is blocked.' : action === 'close' ? 'Assessment closed. Existing records are preserved.' : 'Assessment changes saved.'); }
    } catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <>
    <div className="page-heading"><div><span className="eyebrow">From approval to classroom</span><h1 tabIndex={-1}>Your assessments</h1><p>Prepare a question set, choose your students and publish with confidence.</p></div><Badge tone="purple">Teacher dashboard</Badge></div>
    <div className="assessment-steps"><span><Icon name="book" />Prepare</span><span>→</span><span><Icon name="shield" />Check & publish</span><span>→</span><span>Share reference code</span></div>
    <ErrorNotice error={error} />{notice && <p className="notice success" role="status">{notice}</p>}
    <div className="assessment-layout"><aside className="panel"><div className="section-heading"><h2>Assessment library</h2><span>{page?.total ?? 0}</span></div>
      <button className="btn primary full" disabled={busy} onClick={() => { setDetail(null); setCreating(true); setError(null); setNotice(''); }}>Create assessment</button>
      <button className="text-button" disabled={busy} onClick={() => { setRefresh(n => n + 1); if (detail) void open(detail.id); }}>Refresh assessments</button>
      {page?.total === 0 && <p>No assessments yet. Start with questions from your review queue.</p>}
      {page?.items.map(item => <button className="assessment-list-item" key={item.id} disabled={busy} aria-pressed={detail?.id === item.id} onClick={() => void open(item.id)}><strong>{item.title}</strong><span>{item.question_count} questions · {item.state}</span></button>)}
      {page && page.total > 6 && <Pager offset={offset} total={page.total} busy={busy} change={setOffset} label="assessments" />}
    </aside><div className="assessment-content">
      {creating && <DraftForm busy={busy} save={body => void change('create', body)} />}
      {!creating && !detail && <section className="panel assessment-empty"><Icon name="book" size={40} /><h2>A considered assessment starts here</h2><p>Create an assessment or open one from your library.</p><Link to="/teacher-review">Review your questions</Link></section>}
      {detail && <>
        <section className="panel"><div className="section-heading"><div><span className="eyebrow">{detail.question_count} questions · 1 point each</span><h2>{detail.title}</h2></div><Badge tone={detail.state === 'published' ? 'green' : 'purple'}>{detail.state}</Badge></div>
          <SettingsSummary item={detail} />
          <p><Link to={`/analytics/teacher/${detail.id}`}>View assessment analytics</Link></p>
          <ol className="assessment-question-list">{detail.questions.map(item => <li key={item.version_id}><Link to={`/teacher-review?version=${item.version_id}`}>{item.stem}</Link><small>Version {item.version} · {item.mode === 'mock' ? 'Test content · cannot publish' : item.state}</small></li>)}</ol>
          {detail.state === 'draft' && !detail.can_publish && <p className="notice warning">Publication is blocked. Every question needs current teacher approval and fresh passing checks. Test-generated questions cannot be published.</p>}
          {detail.state === 'draft' && <details><summary>Edit assessment draft</summary><DraftForm key={`${detail.id}-${detail.revision}`} initial={detail} busy={busy} save={body => void change('save', body)} /></details>}
          {detail.state !== 'draft' && <p>Questions and settings are fixed after publication. Students can start admitted attempts and submit their saved answers.</p>}
        </section>
        <Participants key={detail.id} detail={detail} busy={busy} change={body => void change('participants', body)} />
        <Publication key={`${detail.id}-${detail.state}`} detail={detail} busy={busy} change={(action, body) => void change(action, body)} />
      </>}
    </div></div>
  </>;
}

function Pager({ offset, total, busy, change, label }: { offset: number; total: number; busy: boolean; change: (n: number) => void; label: string }) {
  return <div className="assessment-actions"><button type="button" className="btn secondary" disabled={busy || !offset} onClick={() => change(offset - 6)}>Previous {label}</button><button type="button" className="btn secondary" disabled={busy || offset + 6 >= total} onClick={() => change(offset + 6)}>Next {label}</button></div>;
}

function DraftForm({ initial, busy, save }: { initial?: Detail; busy: boolean; save: (body: Record<string, unknown>) => void }) {
  const { authenticated } = useAuth(); const [courses, setCourses] = useState<Page<{ id: string; title: string }> | null>(null); const [courseOffset, setCourseOffset] = useState(0);
  const [questions, setQuestions] = useState<Page<Candidate> | null>(null); const [offset, setOffset] = useState(0); const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState(initial?.questions.map(q => q.version_id) ?? []); const [course, setCourse] = useState(initial?.course_id ?? '');
  const [courseTitle, setCourseTitle] = useState(''); const [savingCourse, setSavingCourse] = useState(false);
  const courseRequest = useRef<AbortController | null>(null);
  useEffect(() => () => courseRequest.current?.abort(), []);
  async function createCourse() {
    const title = courseTitle.trim();
    if (!title || savingCourse || busy) return;
    const controller = new AbortController(); courseRequest.current = controller; setSavingCourse(true); setError(null);
    try {
      const created = await authenticated<{ id: string; title: string }>('/teacher/courses', { body: { title }, signal: controller.signal });
      if (!controller.signal.aborted) {
        setCourses(current => ({ items: [created, ...(current?.items ?? [])], total: (current?.total ?? 0) + 1 }));
        setCourse(created.id); setCourseTitle('');
      }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setSavingCourse(false); }
  }
  useEffect(() => { const controller = new AbortController(); authenticated<Page<Candidate>>(`/teacher/reviews?offset=${offset}&limit=6`, { signal: controller.signal }).then(data => { if (!controller.signal.aborted) setQuestions(data); }).catch(err => { if (!controller.signal.aborted) setError(err); }); return () => controller.abort(); }, [authenticated, offset]);
  useEffect(() => { if (initial) return; const controller = new AbortController(); authenticated<Page<{ id: string; title: string }>>(`/teacher/courses?offset=${courseOffset}&limit=6`, { signal: controller.signal }).then(data => { if (!controller.signal.aborted) setCourses(data); }).catch(err => { if (!controller.signal.aborted) setError(err); }); return () => controller.abort(); }, [authenticated, courseOffset, initial]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || savingCourse || !selected.length || !course) return; const data = new FormData(event.currentTarget);
    save({ title: String(data.get('title')).trim(), version_ids: selected, time_limit_seconds: data.get('minutes') ? Number(data.get('minutes')) * 60 : null, max_attempts: Number(data.get('attempts')), randomize_questions: data.has('shuffle_questions'), randomize_options: data.has('shuffle_options'), release_policy: data.get('release'), ...(initial ? { revision: initial.revision } : { course_id: course }) });
  }
  return <section className={initial ? '' : 'panel'}><h2>{initial ? 'Draft settings' : 'Create your assessment'}</h2><p>Drafts may contain questions still in review. Only eligible questions can be published.</p><ErrorNotice error={error} />
    <form aria-label="Assessment draft" onSubmit={submit}><fieldset disabled={busy || savingCourse}>
      <label className="field">Assessment title<input name="title" aria-label="Assessment title" required maxLength={200} pattern=".*\S.*" defaultValue={initial?.title ?? ''} /></label>
      {!initial && <><label className="field">Course<select aria-label="Course" value={course} onChange={event => setCourse(event.target.value)} required><option value="">Select a course</option>{course && !courses?.items.some(c => c.id === course) && <option value={course}>Selected course (earlier page)</option>}{courses?.items.map(c => <option value={c.id} key={c.id}>{c.title}</option>)}</select></label>{courses?.total === 0 && <p><Link to="/workspace/teacher">Create a course in your teacher workspace</Link> first.</p>}{courses && courses.total > 6 && <Pager offset={courseOffset} total={courses.total} busy={busy} change={setCourseOffset} label="courses" />}</>}
      {!initial && <details><summary>Create a course here</summary><label className="field">New course title<input value={courseTitle} onChange={event => setCourseTitle(event.target.value)} maxLength={200} placeholder="e.g. Prompt Engineering" /></label><button className="btn secondary" type="button" disabled={!courseTitle.trim() || savingCourse || !courses} onClick={() => void createCourse()}>{savingCourse ? 'Creating course…' : 'Create and select course'}</button><p>The new course is selected automatically. Your assessment settings stay here.</p></details>}
      <div className="assessment-field-grid"><label className="field">Time limit in minutes<input aria-label="Time limit in minutes" name="minutes" type="number" min={1} max={240} step={1} placeholder="No time limit" defaultValue={initial?.time_limit_seconds ? initial.time_limit_seconds / 60 : ''} /></label><label className="field">Maximum attempts<input aria-label="Maximum attempts" name="attempts" type="number" required min={1} max={100} step={1} defaultValue={initial?.max_attempts ?? 1} /></label></div>
      <label className="field">Show results<select name="release" defaultValue={initial?.release_policy ?? 'after_submit'}><option value="after_submit">After submission</option><option value="after_close">After the assessment closes</option></select></label>
      <label className="assessment-check"><input type="checkbox" name="shuffle_questions" defaultChecked={initial?.randomize_questions} />Randomize question order</label><label className="assessment-check"><input type="checkbox" name="shuffle_options" defaultChecked={initial?.randomize_options} />Randomize option order</label>
      <p className="muted">The server enforces the time limit and attempt allowance.</p>
      <h3>Select questions <small>({selected.length}/50)</small></h3><p>Selection order sets the assessment order. Remove and reselect a question to move it to the end.</p>
      <button className="text-button" type="button" onClick={() => setSelected([])} disabled={!selected.length}>Clear question selection</button>
      {questions?.items.map(q => <label className="assessment-choice" key={q.id}><input type="checkbox" checked={selected.includes(q.id)} disabled={!selected.includes(q.id) && selected.length >= 50} onChange={e => setSelected(items => e.target.checked ? [...items, q.id] : items.filter(id => id !== q.id))} /><span>{q.stem}<small>v{q.version} · {q.mode === 'mock' ? 'Test content · cannot publish' : q.state}</small></span></label>)}
      {questions?.total === 0 && <p><Link to="/drafts">Create question drafts</Link> to build your assessment.</p>}
      {questions && questions.total > 6 && <Pager offset={offset} total={questions.total} busy={busy} change={setOffset} label="questions" />}
      {(!course || !selected.length) && <p className="notice warning" role="status">To save: {!course && 'select a course'}{!course && !selected.length && ' and '}{!selected.length && 'select at least one question'}. Saving a draft does not approve its questions.</p>}
      {questions?.items.some(q => selected.includes(q.id) && q.mode === 'mock') && <p className="notice warning">Your selection contains test placeholders. They cannot be published. <Link to="/drafts">Generate new questions using local AI</Link>, then review and approve them.</p>}
      <button className="btn primary" disabled={busy || !selected.length || !course} type="submit">{busy ? 'Saving…' : initial ? 'Save assessment draft' : 'Save new assessment'}</button>
    </fieldset></form>
  </section>;
}

function Participants({ detail, busy, change }: { detail: Detail; busy: boolean; change: (body: Record<string, unknown>) => void }) {
  return <section className="panel"><h2>Permitted students</h2><p>A reference code works only for students you allow here. Students must register first.</p>
    <form aria-label="Permit student" onSubmit={event => { event.preventDefault(); if (!busy) change({ email: String(new FormData(event.currentTarget).get('email')).trim().toLowerCase(), active: true }); }}><fieldset disabled={busy || detail.state === 'closed'}><label className="field">Student email<input type="email" name="email" aria-label="Student email" required maxLength={254} placeholder="student@example.com" /></label><button className="btn secondary" type="submit">Allow student</button></fieldset></form>
    {detail.participants.length === 0 && <p>No students allowed yet. Add participants before sharing the code.</p>}
    <ul className="assessment-participants">{detail.participants.map(p => <li key={p.student_id}><div><strong>{p.display_name}</strong><small>{p.email} · {p.active ? 'Allowed' : 'Removed'}</small></div><button aria-label={`${p.active ? 'Remove access' : 'Restore access'} for ${p.email}`} className="text-button" disabled={busy || detail.state === 'closed'} onClick={() => change({ email: p.email, active: !p.active })}>{p.active ? 'Remove access' : 'Restore access'}<span className="sr-only"> for {p.email}</span></button></li>)}</ul>
  </section>;
}

function Publication({ detail, busy, change }: { detail: Detail; busy: boolean; change: (action: string, body: Record<string, unknown>) => void }) {
  const [expiry, setExpiry] = useState(24); const [confirm, setConfirm] = useState(''); const [copied, setCopied] = useState('');
  useEffect(() => { setConfirm(''); setCopied(''); }, [detail]);
  const active = detail.codes.find(code => code.active);
  async function copy() { try { await navigator.clipboard.writeText(detail.issued_code!); setCopied('Code copied.'); } catch { setCopied('Select the code and copy it manually.'); } }
  return <section className="panel"><div className="section-heading"><h2>Publication & reference code</h2><Icon name="shield" /></div>
    {detail.issued_code && <div className="reference-code"><span className="eyebrow">Share with permitted students</span><strong>{detail.issued_code}</strong><button className="btn secondary" onClick={() => void copy()}>Copy reference code</button><p role="status">{copied || 'Save this code now. Reopening the assessment hides it; you can create a replacement.'}</p></div>}
    {active ? <p>Active code expires {date(active.expires_at)}.</p> : <p>No active reference code.</p>}
    {detail.state !== 'closed' && <label className="field">Code expiry in hours<input aria-label="Code expiry in hours" type="number" min={1} max={720} step={1} value={expiry} disabled={busy} onChange={event => setExpiry(Number(event.target.value))} /></label>}
    <div className="assessment-actions">
      {detail.state === 'draft' && <button className="btn primary" disabled={busy || !detail.can_publish || !Number.isInteger(expiry) || expiry < 1 || expiry > 720} onClick={() => setConfirm('publish')}>Publish assessment</button>}
      {detail.state === 'published' && <><button className="btn primary" disabled={busy || !Number.isInteger(expiry) || expiry < 1 || expiry > 720} onClick={() => setConfirm('rotate')}>Create replacement code</button><button className="btn secondary" disabled={busy || !active} onClick={() => setConfirm('revoke')}>Revoke codes</button><button className="btn danger" disabled={busy} onClick={() => setConfirm('close')}>Close assessment</button></>}
    </div>
    {confirm && <div className="notice warning" role="group" aria-label="Confirm assessment action"><p>{confirm === 'publish' ? 'Publish these exact question versions and settings? They cannot be edited afterward. All release checks will run again.' : confirm === 'rotate' ? 'Replace the code? Students must join again with the new code before a new attempt.' : confirm === 'revoke' ? 'Revoke all codes and block new access? Existing records will be preserved.' : 'Close this assessment permanently and revoke its codes? Existing records will be preserved.'}</p><button className="btn secondary" disabled={busy} onClick={() => setConfirm('')}>Cancel</button><button className="btn primary" disabled={busy} onClick={() => change(confirm, confirm === 'publish' ? { revision: detail.revision, expiry_hours: expiry } : confirm === 'rotate' ? { expiry_hours: expiry } : {})}>Confirm {confirm === 'rotate' ? 'replacement' : confirm}</button></div>}
    <p>Expiry, removal and revocation block new access. Codes do not grant access to private documents or answer keys.</p>
  </section>;
}

function SettingsSummary({ item }: { item: Settings }) {
  return <div className="assessment-settings"><span><strong>{item.time_limit_seconds ? `${item.time_limit_seconds / 60} min` : 'Untimed'}</strong>Time limit</span><span><strong>{item.max_attempts}</strong>Maximum attempts</span><span><strong>{item.release_policy === 'after_close' ? 'After close' : 'After submission'}</strong>Results</span><span><strong>{item.randomize_questions ? 'Random' : 'Fixed'}</strong>Question order</span><span><strong>{item.randomize_options ? 'Random' : 'Fixed'}</strong>Option order</span></div>;
}

export function JoinAssessment() {
  const { user } = useAuth();
  if (!user?.roles.includes('student')) return <section className="panel"><h1 tabIndex={-1}>Student access required</h1><Link to="/workspace">Go to workspace</Link></section>;
  return <JoinWorkspace />;
}

function JoinWorkspace() {
  const navigate = useNavigate(); const startRetry = useRef<{ id: string; key: string } | null>(null);
  const { authenticated } = useAuth(); const [page, setPage] = useState<Page<Admission> | null>(null); const [offset, setOffset] = useState(0); const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [joined, setJoined] = useState<Admission | null>(null); const [code, setCode] = useState('');
  const pending = useRef<AbortController | null>(null); useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => { const controller = new AbortController(); authenticated<Page<Admission>>(`/student/assessments?offset=${offset}&limit=6`, { signal: controller.signal }).then(data => { if (!controller.signal.aborted) setPage(data); }).catch(err => { if (!controller.signal.aborted) setError(err); }); return () => controller.abort(); }, [authenticated, offset, refresh]);
  async function start(id: string) {
    if (busy) return; setBusy(true); setError(null);
    if (startRetry.current?.id !== id) startRetry.current = { id, key: crypto.randomUUID() };
    const controller = new AbortController(); pending.current = controller;
    try { const result = await authenticated<{ id: string }>(`/student/assessments/${id}/attempts`, { body: { idempotency_key: startRetry.current.key }, signal: controller.signal }); if (!controller.signal.aborted) navigate(`/attempts/${result.id}`); }
    catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function join(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setJoined(null);
    try { const result = await authenticated<Admission>('/student/assessments/join', { body: { code }, signal: controller.signal }); if (!controller.signal.aborted) { setJoined(result); setCode(''); setOffset(0); setRefresh(n => n + 1); } }
    catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <><div className="page-heading"><div><span className="eyebrow">Your classroom connection</span><h1 tabIndex={-1}>Join an assessment</h1><p>Use the code your teacher shared with you.</p></div><Badge tone="green">Student dashboard</Badge></div>
    <div className="assessment-join-grid"><section className="panel"><Icon name="book" size={30} /><h2>A code opens the classroom</h2><p>Your teacher must allow your registered email before you can join.</p><ErrorNotice error={error} />
      <form onSubmit={join} aria-label="Join assessment"><fieldset disabled={busy}><label className="field">Reference code<input aria-label="Reference code" name="code" value={code} onChange={event => setCode(event.target.value)} autoComplete="off" spellCheck={false} required maxLength={64} placeholder="MCQ-XXXX-XXXX-XXXX-XXXX-XXXX" /></label><button className="btn primary" type="submit" disabled={busy || !code.trim()}>{busy ? 'Checking code…' : 'Join assessment'}</button></fieldset></form>
      {joined && <p className="notice success" role="status">{joined.available ? `You joined ${joined.title}.` : 'Your admission was recorded, but access is currently unavailable.'} Open it below when you are ready.</p>}
      <p>Joining does not start an attempt or reveal questions and answers.</p></section>
      <section className="panel"><div className="section-heading"><h2>Your joined assessments</h2><button className="text-button" disabled={busy} onClick={() => setRefresh(n => n + 1)}>Refresh joined assessments</button></div>
        {page?.total === 0 && <p>No joined assessments yet. Your teacher can help you get started.</p>}
        {page?.items.map(item => <article className="joined-assessment" key={item.id}><div className="section-heading"><h3>{item.title}</h3><Badge tone={item.available ? 'green' : 'muted'}>{item.available ? 'Access confirmed' : 'Unavailable'}</Badge></div><p>{item.question_count} questions</p><SettingsSummary item={item} /><p>{item.available ? 'Start when you are ready. Timed attempts begin immediately.' : 'The code may have expired or been replaced, access may have changed, or the assessment may be closed. Ask your teacher.'}</p>{item.available && <button className="btn primary" disabled={busy} onClick={() => void start(item.id)}>Start or resume assessment</button>}<p><Link to="/workspace/student">Resume an existing attempt from your history</Link></p></article>)}
        {page && page.total > 6 && <Pager offset={offset} total={page.total} busy={busy} change={setOffset} label="joined assessments" />}
      </section></div></>;
}
