import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Field, Icon } from '../ui';
import './teacher.css';
import { QuickActions } from '../QuickActions';

interface Course { id: string; title: string; created_at: string; topic_count: number }
interface Topic { id: string; name: string }
interface CourseDetail extends Course { topics: Topic[] }
interface CoursePage { items: Course[]; total: number; offset: number; limit: number }
interface Dashboard {
  counts: { courses: number; materials: number; questions: number; assessments: number };
  recent_assessments: { id: string; title: string; course_title: string; state: string; created_at: string }[];
}
const date = (value: string) => new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
const cancelled = (error: unknown) => error instanceof DOMException && error.name === 'AbortError';

export function TeacherDashboard() {
  const { user, authenticated } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [courses, setCourses] = useState<CoursePage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [saved, setSaved] = useState('');
  const createButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setData(null); setCourses(null);
    async function load() {
      try {
        // Sequential requests keep the one-computer database pool small.
        const summary = await authenticated<Dashboard>('/teacher/dashboard', { signal: controller.signal });
        const page = await authenticated<CoursePage>(`/teacher/courses?offset=${offset}&limit=6`, { signal: controller.signal });
        if (!controller.signal.aborted) { setData(summary); setCourses(page); }
      } catch (err) { if (!controller.signal.aborted && !cancelled(err)) setError(err); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load(); return () => controller.abort();
  }, [authenticated, offset, revision]);
  const reload = useCallback(() => setRevision(value => value + 1), []);
  const created = (course: Course) => {
    setCreating(false); setSaved(`Course “${course.title}” created.`); setOffset(0); reload(); setSelected(course.id);
  };
  const closeCourse = () => { setSelected(null); createButton.current?.focus(); };
  const topicAdded = useCallback(() => { setSaved('Topic added to your course.'); reload(); }, [reload]);
  const metrics = [
    ['courses', 'Your courses', 'Organized teaching spaces', 'book'],
    ['materials', 'Study materials', 'Active material records', 'layers'],
    ['questions', 'Question bank', 'Active questions · all review states', 'spark'],
    ['assessments', 'Classroom assessments', 'Draft, published and closed', 'grid'],
  ] as const;
  return <>
    <div className="page-heading"><div><span className="eyebrow">Teacher dashboard</span><h1 tabIndex={-1}>Welcome, {user?.display_name.split(' ')[0]}<span className="heading-period">.</span></h1><p>Manage your study materials, questions and classroom assessments.</p></div><button className="btn primary" ref={createButton} onClick={() => { setCreating(true); setSaved(''); }}>Create course <Icon name="arrow" size={16} /></button></div>
    {saved && <div className="notice success" role="status">{saved}</div>}
    {creating && <CreateCourse onCreated={created} onCancel={() => { setCreating(false); createButton.current?.focus(); }} />}
    <div className="teacher-status"><span>Overview · your records only</span><button className="text-button" disabled={loading} onClick={reload}>{loading ? 'Loading…' : 'Refresh overview'}</button></div>
    <ErrorNotice error={error} />{error ? <button className="btn secondary" onClick={reload}>Retry dashboard</button> : null}
    <section className="teacher-metrics" aria-label="Your teaching overview" aria-busy={loading}>{metrics.map(([key, label, hint, icon]) => <article className="metric" key={key}><div className="metric-label"><span>{label}</span><Icon name={icon} size={19} /></div><strong aria-label={`${label}: ${data ? data.counts[key] : 'unavailable'}`}>{data ? data.counts[key].toLocaleString() : '—'}</strong><small>{hint}</small></article>)}</section>
    <QuickActions teacher />
    <div className="teacher-grid"><div><section className="panel courses-panel" aria-labelledby="courses-title"><div className="section-heading"><div><h2 id="courses-title">Your courses</h2><p>Set up the subjects and topics you teach.</p></div><Badge tone="green">Available now</Badge></div>
      {loading ? <p role="status" className="loading-copy">Loading your courses…</p> : courses ? <>
        {courses.items.length ? <div className="course-list">{courses.items.map(course => <button className="course-row" key={course.id} onClick={() => setSelected(course.id)}><span className="feature-icon"><Icon name="book" /></span><span><strong>{course.title}</strong><small>{course.topic_count} {course.topic_count === 1 ? 'topic' : 'topics'} · Created {date(course.created_at)}</small></span><Icon name="arrow" size={17} /></button>)}</div> : <div className="teacher-empty"><span className="feature-icon"><Icon name="book" size={25} /></span><h3>{courses.total ? 'No courses on this page' : 'Your first course starts here'}</h3><p>{courses.total ? 'Go back to an earlier page to see your courses.' : 'Create a course and add its topics, then use the shortcuts above to prepare an assessment.'}</p>{!courses.total && <button className="btn secondary" onClick={() => setCreating(true)}>Create your first course</button>}</div>}
        {courses.total > 6 && <div className="pagination"><button className="btn secondary" disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 6))}>Previous</button><span>Page {Math.floor(offset / 6) + 1} · {courses.total} courses</span><button className="btn secondary" disabled={offset + 6 >= courses.total} onClick={() => setOffset(value => value + 6)}>Next</button></div>}
      </> : <p className="unavailable-copy">Course data is unavailable. Retry the overview to reconnect.</p>}
    </section>{selected && <CourseEditor key={selected} id={selected} onClose={closeCourse} onAdded={topicAdded} />}</div>
    <aside className="teacher-roadmap"><span className="eyebrow light">Your teaching workflow</span><h2>From material<br />to meaningful questions.</h2><p>Organize source material, review questions, publish assessments and investigate student reports.</p><ol><li><span>01</span><div><strong>Organize courses & topics</strong><small>Available now</small></div><Icon name="check" size={17} /></li><li><span>02</span><div><strong>Prepare source material</strong><small>PDF upload ready · test generation available</small></div></li><li><span>03</span><div><strong>Review & publish</strong><small>Available · evidence-backed approval</small></div></li><li><span>04</span><div><strong>Understand performance</strong><small>Feedback review & analytics available</small></div></li></ol></aside></div>
    <section className="panel assessments-panel"><div className="section-heading"><div><h2>Recent classroom assessments</h2><p>Latest five records, shown when they exist.</p></div><Badge>Assessment library available</Badge></div>{loading ? <p role="status">Loading assessment records…</p> : data?.recent_assessments.length ? <div className="assessment-list">{data.recent_assessments.map(item => <article key={item.id}><div><h3>{item.title}</h3><p>{item.course_title} · {date(item.created_at)}</p></div><Badge>{item.state}</Badge></article>)}</div> : data ? <div className="assessment-empty"><Icon name="grid" size={27} /><div><h3>No classroom assessments yet</h3><p>Create and publish eligible questions from Assessments. Recent records will appear here.</p></div></div> : <p className="unavailable-copy">Assessment records are unavailable.</p>}</section>
  </>;
}

function CreateCourse({ onCreated, onCancel }: { onCreated(course: Course): void; onCancel(): void }) {
  const { authenticated } = useAuth(); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const title = String(new FormData(event.currentTarget).get('title')).trim(); setBusy(true); setError(null);
    try { onCreated(await authenticated<Course>('/teacher/courses', { body: { title } })); } catch (err) { if (!cancelled(err)) setError(err); } finally { setBusy(false); }
  }
  return <section className="panel course-form"><h2>Create a course</h2><p>Use a clear subject or class name. You can add topics next.</p><ErrorNotice error={error} /><form onSubmit={submit} aria-label="Create course"><fieldset disabled={busy}><Field autoFocus label="Course title" name="title" required maxLength={200} pattern=".*\S.*" placeholder="e.g. Database Management Systems" hint="1–200 characters. Course titles must be unique within your workspace." /><div className="form-actions"><button className="btn primary" type="submit" aria-busy={busy}>{busy ? 'Saving course…' : 'Save course'}</button><button className="btn secondary" type="button" onClick={onCancel}>Cancel</button></div></fieldset></form></section>;
}

function CourseEditor({ id, onClose, onAdded }: { id: string; onClose(): void; onAdded(): void }) {
  const { authenticated } = useAuth(); const [data, setData] = useState<CourseDetail | null>(null); const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false); const [revision, setRevision] = useState(0); const [loading, setLoading] = useState(true);
  const heading = useRef<HTMLHeadingElement>(null); const mounted = useRef(true);
  useEffect(() => { mounted.current = true; heading.current?.focus(); heading.current?.scrollIntoView?.({ block: 'nearest' }); return () => { mounted.current = false; }; }, []);
  useEffect(() => { const controller = new AbortController(); setLoading(true); setError(null); void authenticated<CourseDetail>(`/teacher/courses/${id}`, { signal: controller.signal }).then(result => { if (!controller.signal.aborted) setData(result); }).catch(err => { if (!controller.signal.aborted && !cancelled(err)) setError(err); }).finally(() => { if (!controller.signal.aborted) setLoading(false); }); return () => controller.abort(); }, [id, revision, authenticated]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget; const title = String(new FormData(form).get('topic')).trim(); setBusy(true); setError(null);
    try { await authenticated<Topic>(`/teacher/courses/${id}/topics`, { body: { title } }); if (mounted.current) { form.reset(); setRevision(value => value + 1); onAdded(); } } catch (err) { if (mounted.current && !cancelled(err)) setError(err); } finally { if (mounted.current) setBusy(false); }
  }
  return <section className="panel course-editor" aria-label="Course topics"><div className="section-heading"><div><span className="eyebrow">Course topics</span><h2 ref={heading} tabIndex={-1}>{data?.title ?? 'Opening course…'}</h2></div><button className="btn secondary" onClick={onClose} disabled={busy}>Close course</button></div><ErrorNotice error={error} />{loading ? <p role="status">Loading course topics…</p> : error && !data ? <button className="btn secondary" onClick={() => setRevision(value => value + 1)}>Retry course</button> : data && <><p className="topic-summary">{data.topic_count} of 100 topics · Topics help organize future question generation.</p>{data.topics.length ? <ul className="topic-list">{data.topics.map(topic => <li key={topic.id}><Icon name="check" size={15} />{topic.name}</li>)}</ul> : <p className="topic-summary">No topics yet. Add your first topic below.</p>}{data.topic_count < 100 && <form onSubmit={submit} aria-label="Add topic"><fieldset disabled={busy}><Field label="Topic name" name="topic" required maxLength={200} pattern=".*\S.*" placeholder="e.g. Relational algebra" /><button className="btn primary" type="submit" aria-busy={busy}>{busy ? 'Saving topic…' : 'Add topic'}</button></fieldset></form>}{data.topic_count > 100 && <p className="topic-summary">Showing the first 100 topics.</p>}</>}</section>;
}
