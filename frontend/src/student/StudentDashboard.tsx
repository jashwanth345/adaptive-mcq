import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import './student.css';
import { QuickActions } from '../QuickActions';

type Difficulty = 'easy' | 'medium' | 'hard';
interface Preferences { preferred_difficulty: Difficulty }
interface Dashboard {
  preferences: Preferences;
  counts: { courses: number; materials: number; submitted_attempts: number; feedback: number };
  courses: { id: string; title: string; joined_at: string }[];
}
interface AttemptPage {
  items: { id: string; title: string; kind: 'classroom' | 'practice'; state: 'in_progress' | 'submitted' | 'expired'; attempt_number: number; started_at: string; submitted_at: string | null }[];
  total: number; offset: number; limit: number;
}
const shortDate = (value: string) => new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
const isCancelled = (err: unknown) => err instanceof DOMException && err.name === 'AbortError';
const statusLabels = { in_progress: 'In progress', submitted: 'Submitted', expired: 'Expired' };

export function StudentDashboard() {
  const { user, authenticated } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [history, setHistory] = useState<AttemptPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setData(null); setHistory(null);
    async function load() {
      try {
        const summary = await authenticated<Dashboard>('/student/dashboard', { signal: controller.signal });
        const attempts = await authenticated<AttemptPage>(`/student/attempts?offset=${offset}&limit=6`, { signal: controller.signal });
        if (!controller.signal.aborted) { setData(summary); setHistory(attempts); }
      } catch (err) { if (!controller.signal.aborted && !isCancelled(err)) setError(err); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load(); return () => controller.abort();
  }, [authenticated, offset, revision]);
  const metrics = [
    ['courses', 'Enrolled courses', 'Active course memberships', 'book'],
    ['materials', 'Your study materials', 'Personal, active material records', 'layers'],
    ['submitted_attempts', 'Submitted attempts', 'Classroom and personal practice', 'check'],
    ['feedback', 'Your feedback', 'Reports you have submitted', 'chart'],
  ] as const;
  return <>
    <div className="page-heading"><div><span className="eyebrow">Student dashboard</span><h1 tabIndex={-1}>Welcome, {user?.display_name.split(' ')[0]}<span className="heading-period">.</span></h1><p>A place to organize your learning and see your activity.</p></div><button className="btn secondary" onClick={() => setRevision(value => value + 1)} disabled={loading}>{loading ? 'Loading dashboard…' : 'Refresh dashboard'}</button></div>
    <section className="student-banner"><div><Badge tone="purple">Your learning, at your pace</Badge><h2>Small steps.<br />A stronger understanding.</h2><p>See your courses and activity here. Choose a starting difficulty for your personal practice.</p></div><div className="student-banner-art" aria-hidden="true"><span><Icon name="book" size={36} /></span><span><Icon name="spark" size={32} /></span><span className="student-art-caption">Read. Practice. Reflect.</span></div></section>
    <div className="student-section-label"><span>Your records · visible only to your account</span><span>No estimated performance</span></div>
    <ErrorNotice error={error} />{error && <button className="btn secondary" onClick={() => setRevision(value => value + 1)}>Retry student dashboard</button>}
    <section className="student-metrics" aria-label="Your learning overview" aria-busy={loading}>{metrics.map(([key, title, hint, icon]) => <article key={key}><div><span>{title}</span><Icon name={icon} size={18} /></div><strong aria-label={`${title}: ${data ? data.counts[key] : 'unavailable'}`}>{data ? data.counts[key].toLocaleString() : '—'}</strong><small>{hint}</small></article>)}</section>
    <QuickActions />
    <div className="student-columns"><section className="panel student-courses"><div className="section-heading"><div><h2>Your courses</h2><p>Your six most recent active enrollments.</p></div><Icon name="book" size={23} /></div>
      {loading ? <p role="status">Loading your courses…</p> : !data ? <p>Course records are unavailable. Retry the dashboard to reconnect.</p> : data.courses.length ? <><ul className="student-course-list">{data.courses.map(course => <li key={course.id}><span className="feature-icon"><Icon name="book" /></span><div><h3>{course.title}</h3><p>Joined {shortDate(course.joined_at)}</p></div><Badge tone="green">Enrolled</Badge></li>)}</ul>{data.counts.courses > 6 && <p>Showing 6 of {data.counts.courses} active courses.</p>}</> : <div className="student-empty"><span className="feature-icon"><Icon name="book" size={24} /></span><h3>No enrolled courses yet</h3><p>Join a teacher assessment with a valid reference code to enroll in its course.</p></div>}
    </section><section className="panel student-preferences"><div className="section-heading"><div><h2>Practice preference</h2><p>Choose your starting point.</p></div><Badge tone="green">Available now</Badge></div>
      {data ? <PreferenceForm key={`${revision}-${offset}`} initial={data.preferences.preferred_difficulty} /> : <p>{loading ? 'Loading your preference…' : 'Your preference is unavailable until the dashboard reconnects.'}</p>}
    </section></div>
    <section className="panel student-history"><div className="section-heading"><div><h2>Attempt history</h2><p>Your recorded attempts, most recent first.</p></div><Badge>Saved attempts</Badge></div>
      {loading ? <p role="status">Loading attempt history…</p> : !history ? <p>Attempt records are unavailable.</p> : history.items.length ? <div className="history-table-wrap"><table><caption className="sr-only">Your recorded assessment attempts</caption><thead><tr><th scope="col">Assessment</th><th scope="col">Type</th><th scope="col">Started</th><th scope="col">Status</th></tr></thead><tbody>{history.items.map(item => <tr key={item.id}><td><Link to={`/attempts/${item.id}`}>{item.title}</Link><small>Attempt {item.attempt_number}</small></td><td>{item.kind === 'classroom' ? 'Classroom' : 'Personal practice'}</td><td>{shortDate(item.started_at)}</td><td><Badge tone={item.state === 'submitted' ? 'green' : 'muted'}>{statusLabels[item.state]}</Badge></td></tr>)}</tbody></table></div> : <div className="student-history-empty"><Icon name="layers" size={27} /><div><h3>{history.total ? 'No attempts on this page' : 'Your learning history starts here'}</h3><p>{history.total ? 'Go back to an earlier page to view your records.' : 'No attempts are recorded for your account. Join a teacher assessment or open My learning to start eligible private practice.'}</p></div></div>}
      {history && history.total > 6 && <div className="student-pagination"><button className="btn secondary" disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 6))}>Previous attempts</button><span>Page {Math.floor(offset / 6) + 1} · {history.total} attempts</span><button className="btn secondary" disabled={offset + 6 >= history.total} onClick={() => setOffset(value => value + 6)}>Next attempts</button></div>}
      <p className="history-note">Open an attempt to resume saved progress or view results when released. Older imported records may only have activity metadata.</p>
    </section>
    <div className="section-heading"><div><h2>Your next learning tools</h2><p>Continue with a classroom assessment or safe private practice.</p></div></div><div className="feature-grid">{[
      ['Take an assessment', 'Complete the questions in your teacher’s published assessment.', 'book'],
      ['Practice your way', 'Create private question drafts from your material. Test generation is clearly labelled.', 'spark'],
      ['See your progress', 'View provisional topic profiles and transparent adaptive suggestions.', 'chart'],
    ].map(([title, description, icon], i) => <article className="feature-card" key={title}><div className="feature-top"><span className={`feature-icon accent-${i}`}><Icon name={icon as 'book' | 'spark' | 'chart'} /></span><Badge tone="green">Available</Badge></div><h3>{title}</h3><p>{description}</p><Link to={i === 0 ? '/join-assessment' : '/learning'}>{i === 0 ? 'Join assessment' : 'Open My learning'}</Link></article>)}</div>
  </>;
}

function PreferenceForm({ initial }: { initial: Difficulty }) {
  const { authenticated } = useAuth();
  const [choice, setChoice] = useState(initial); const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState('');
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || choice === saved) return; setBusy(true); setError(null); setNotice('');
    try { const result = await authenticated<Preferences>('/student/preferences', { body: { preferred_difficulty: choice } }); if (mounted.current) { setSaved(result.preferred_difficulty); setNotice('Practice preference saved.'); } }
    catch (err) { if (mounted.current && !isCancelled(err)) setError(err); }
    finally { if (mounted.current) setBusy(false); }
  }
  return <form onSubmit={submit} aria-label="Practice preference"><ErrorNotice error={error} /><fieldset disabled={busy}><legend>Starting difficulty</legend><div className="difficulty-options">{(['easy', 'medium', 'hard'] as const).map(value => <label key={value} className={choice === value ? 'selected' : ''}><input type="radio" name="difficulty" value={value} checked={choice === value} onChange={() => { setChoice(value); setNotice(''); }} />{value[0].toUpperCase() + value.slice(1)}</label>)}</div><p className="preference-description">This sets the starting level used by your personal practice recommendations. It does not change a teacher’s assessment or measure your mastery.</p><button className="btn primary" type="submit" disabled={busy || choice === saved} aria-busy={busy}>{busy ? 'Saving preference…' : 'Save preference'}</button>{choice !== saved && <span className="unsaved-label">Unsaved change</span>}</fieldset>{notice && <p className="saved-preference" role="status">{notice}</p>}</form>;
}
