import { Component, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import { request, type Role } from './api';
import { useAuth } from './auth';
import { Badge, Brand, ErrorNotice, Field, Icon, PasswordField } from './ui';
import { TeacherDashboard } from './teacher/TeacherDashboard';
import { StudentDashboard } from './student/StudentDashboard';
import { Materials } from './materials/Materials';
import { Drafts } from './generator/Drafts';
import { Attempt } from './attempts/Attempt';
import { FeedbackHistory, FeedbackQueue, FeedbackDetail } from './feedback/Feedback';
import { Learning } from './attempts/Learning';
import { TeacherAssessments, JoinAssessment } from './assessments/Assessments';
import { TeacherReview } from './teacher/TeacherReview';
import { Analytics } from './analytics/Analytics';
import { Evaluation } from './evaluation/Evaluation';
import { Landing } from './Landing';

function RouteFocus() {
  const { pathname } = useLocation();
  useEffect(() => {
    const heading = document.querySelector<HTMLHeadingElement>('h1');
    heading?.focus();
    document.title = `${heading?.textContent ?? 'Workspace'} · Adaptive MCQ`;
  }, [pathname]);
  return null;
}
class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <main className="standalone"><Brand /><h1>Let’s try that again</h1><p>The page could not be displayed. Reload to start a fresh session.</p><button className="btn primary" onClick={() => window.location.reload()}>Reload page</button></main> : this.props.children;
  }
}
export function App() {
  return <ErrorBoundary><a className="skip-link" href="#main">Skip to content</a><Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<AuthPage />} /><Route path="/register" element={<AuthPage register />} />
    <Route element={<RequireAuth />}><Route element={<Shell />}>
      <Route path="/workspace" element={<WorkspaceRedirect />} />
      <Route path="/workspace/:role" element={<Workspace />} />
      <Route path="/account" element={<Account />} />
      <Route path="/materials" element={<Materials />} />
      <Route path="/drafts" element={<Drafts />} />
      <Route path="/teacher-review" element={<TeacherReview />} />
      <Route path="/assessments" element={<TeacherAssessments />} />
      <Route path="/join-assessment" element={<JoinAssessment />} />
      <Route path="/attempts/:attemptId" element={<Attempt />} />
      <Route path="/learning" element={<Learning />} />
      <Route path="/analytics/student" element={<Analytics />} />
      <Route path="/analytics/teacher" element={<Analytics teacher />} />
      <Route path="/analytics/teacher/:assessmentId" element={<Analytics teacher />} />
      <Route path="/evaluation" element={<Evaluation />} />
      <Route path="/feedback" element={<FeedbackHistory />} />
      <Route path="/feedback-review" element={<FeedbackQueue />} />
      <Route path="/feedback-review/:versionId" element={<FeedbackDetail />} />
    </Route></Route>
    <Route path="*" element={<NotFound />} />
  </Routes><RouteFocus /></ErrorBoundary>;
}

function AuthPage({ register = false }: { register?: boolean }) {
  const auth = useAuth(); const navigate = useNavigate();
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [signupRole, setSignupRole] = useState<Role>('student');
  const pending = useRef<AbortController | null>(null);
  useEffect(() => { setError(null); setRegistered(false); setBusy(false); return () => pending.current?.abort(); }, [register]);
  if (auth.user) return <Navigate to="/workspace" replace />;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const data = new FormData(event.currentTarget);
    if (register && String(data.get('password')) !== String(data.get('confirm'))) { setError(new Error('mismatch')); return; }
    setBusy(true); setError(null); auth.clearNotice();
    const controller = new AbortController(); pending.current = controller;
    try {
      if (register) {
        await request(signupRole === 'teacher' ? '/auth/register-teacher' : '/auth/register', { body: { display_name: String(data.get('name')).trim(), email: String(data.get('email')).trim(), password: String(data.get('password')) }, signal: controller.signal });
        if (!controller.signal.aborted) setRegistered(true);
      } else { await auth.login(String(data.get('email')), String(data.get('password')), controller.signal); }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <div className="auth-layout">
    <aside className="auth-story" aria-label="About Adaptive MCQ"><Brand light />
      <div className="story-main"><div className="eyebrow light">A more thoughtful way to assess</div>
        <h2>Every question.<br />A step <em>forward.</em></h2>
        <p>A shared space for teachers and students, designed around reliable questions and individual learning.</p>
        <div className="concept" aria-label="Planned learning cycle"><div className="concept-orbit" /><div className="concept-center"><Icon name="spark" size={30} /><span>Learning<br />that adapts</span></div>
          <span className="concept-node node-1"><Icon name="book" />Study material</span><span className="concept-node node-2"><Icon name="shield" />Verified questions</span><span className="concept-node node-3"><Icon name="chart" />Student feedback</span>
        </div><span className="story-caption">Local workspace · Test generation is clearly labelled</span>
      </div><div className="story-footer"><span className="status-dot" />Runs on your computer<span>Built for learning.</span></div>
    </aside>
    <main className="auth-main" id="main"><div className="auth-top"><Link to="/">← Back to home</Link><Badge tone="green">Local workspace</Badge></div>
      <div className="auth-card" key={register ? 'register' : 'login'}>
        <Brand />
        <span className="eyebrow">{register ? 'Your learning starts here' : 'Your assessment workspace'}</span>
        <h1 tabIndex={-1}>{registered ? 'You’re ready to sign in' : register ? 'Create your account' : 'Welcome back'}</h1>
        <p className="lead">{registered ? `Your ${signupRole} account has been created. Sign in to open your workspace.` : register ? 'Choose Teacher or Student to create your workspace.' : 'Teacher & Student Login — use your registered email and password. Your dashboard opens automatically.'}</p>
        {auth.notice && <div className="notice success" role="status">{auth.notice}</div>}
        {registered ? <button className="btn primary full" onClick={() => navigate('/login')}>Continue to sign in <Icon name="arrow" /></button> : <>
          {error instanceof Error && error.message === 'mismatch' ? <div className="notice error" role="alert">The passwords do not match.</div> : <ErrorNotice error={error} />}
          <form onSubmit={submit} aria-label={register ? `${signupRole === 'teacher' ? 'Teacher' : 'Student'} registration` : 'Sign in'}>
            <fieldset disabled={busy}>
              {register && <label className="field">Account type<select value={signupRole} onChange={event => setSignupRole(event.target.value as Role)}><option value="student">Student — learn and practice</option><option value="teacher">Teacher — create and manage assessments</option></select></label>}
              {register && <Field label="Full name" name="name" autoComplete="name" required maxLength={160} pattern=".*\S.*" placeholder="Your full name" />}
              <Field label="Email address" name="email" type="email" autoComplete="username" required maxLength={254} placeholder="you@example.com" />
              <PasswordField name="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 12 : 1} maxLength={128} hint={register ? 'Use 12–128 characters. Spaces are allowed.' : undefined} />
              {register && <PasswordField label="Confirm password" name="confirm" autoComplete="new-password" required minLength={12} maxLength={128} />}
              <button className="btn primary full" type="submit" aria-busy={busy}>{busy ? (register ? 'Creating account…' : 'Signing in…') : (register ? `Create ${signupRole} account` : 'Sign in')}<Icon name="arrow" /></button>
            </fieldset>
          </form>
          <p className="switch-auth">{register ? 'Already have an account?' : 'New to Adaptive MCQ?'} {busy ? <span>Please wait…</span> : <Link to={register ? '/login' : '/register'}>{register ? 'Sign in' : 'Create teacher or student account'}</Link>}</p>
          <div className="quiet-note"><Icon name="shield" size={18} /><span>{register ? 'Each teacher manages their own materials, questions and assessments. Existing student accounts are not changed by signing up again.' : 'For your privacy, refreshing or closing this page requires signing in again.'}</span></div>
        </>}
      </div>
      <footer className="auth-footer">Sri Venkateswara College of Engineering (Autonomous)<br /><span>Department of CSE (Artificial Intelligence and Machine Learning)</span></footer>
    </main>
  </div>;
}
function RequireAuth() { return useAuth().user ? <Outlet /> : <Navigate to="/login" replace />; }
function WorkspaceRedirect() {
  const { user } = useAuth(); const role = user?.roles.includes('teacher') ? 'teacher' : 'student';
  return <Navigate to={`/workspace/${role}`} replace />;
}
function Shell() {
  const { user, logout, warning, refresh } = useAuth(); const { pathname } = useLocation();
  const [mobile, setMobile] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  useEffect(() => { setMobile(false); setError(null); }, [pathname]);
  async function signOut() { setBusy(true); setError(null); try { await logout(); } catch (err) { setError(err); } finally { setBusy(false); } }
  return <div className="app-layout">
    <header className="mobile-header"><Brand /><button className="icon-button" onClick={() => setMobile(!mobile)} aria-label="Toggle navigation" aria-expanded={mobile} aria-controls="navigation"><Icon name="menu" /></button></header>
    <aside id="navigation" className={`sidebar ${mobile ? 'open' : ''}`}><Brand /><div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{user?.roles.map(role => <NavLink key={role} to={`/workspace/${role}`}><Icon name="grid" /><span>{role === 'teacher' ? 'Teacher' : 'Student'} dashboard</span></NavLink>)}
        <NavLink to="/materials"><Icon name="book" /><span>Study materials</span></NavLink>
        <NavLink to="/drafts"><Icon name="spark" /><span>Generate MCQs</span></NavLink>
        {user?.roles.includes('teacher') && <NavLink to="/teacher-review"><Icon name="shield" /><span>Teacher review</span></NavLink>}
        {user?.roles.includes('teacher') && <NavLink to="/assessments"><Icon name="book" /><span>Assessments</span></NavLink>}
        {user?.roles.includes('student') && <NavLink to="/join-assessment"><Icon name="book" /><span>Join assessment</span></NavLink>}
        {user?.roles.includes('student') && <NavLink to="/learning"><Icon name="chart" /><span>My learning</span></NavLink>}
        {user?.roles.includes('student') && <NavLink to="/analytics/student"><Icon name="chart" /><span>My analytics</span></NavLink>}
        {user?.roles.includes('teacher') && <NavLink to="/analytics/teacher"><Icon name="chart" /><span>Classroom analytics</span></NavLink>}
        {user?.roles.includes('teacher') && <NavLink to="/evaluation"><Icon name="layers" /><span>Evaluation lab</span></NavLink>}
        {user?.roles.includes('student') && <NavLink to="/feedback"><Icon name="book" /><span>My feedback</span></NavLink>}
        <NavLink to="/feedback-review"><Icon name="shield" /><span>Feedback review</span></NavLink>
        <NavLink to="/account"><Icon name="user" /><span>My account</span></NavLink>
      </nav>
      <div className="sidebar-bottom"><div className="local-label"><span className="status-dot" />Local workspace</div><p>Your learning, on your computer.</p><div className="sidebar-user"><span className="avatar">{user?.display_name.slice(0, 1).toUpperCase()}</span><div><strong>{user?.display_name}</strong><small>{user?.roles.join(' & ') || 'Account'}</small></div></div><button className="signout" onClick={() => void signOut()} disabled={busy}><Icon name="logout" />{busy ? 'Signing out…' : 'Sign out'}</button><ErrorNotice error={error} /></div>
    </aside>
    <div className="app-content"><header className="topbar"><span>Learn. Practice. Improve.</span><div className="topbar-identity"><Badge tone="green">Local workspace</Badge><span className="avatar">{user?.display_name.slice(0, 1).toUpperCase()}</span><span><strong>{user?.display_name}</strong><small>{user?.roles.join(' & ')}</small></span></div></header>
      <main id="main" className="workspace-main">{warning && <div className="notice warning" role="status">{warning}<button className="text-button" onClick={() => void refresh()}>Retry connection</button></div>}<Outlet /></main>
      <footer className="workspace-footer"><span>Adaptive MCQ · Academic year 2026–2027</span><span>Designed for teachers. Centered on students.</span></footer>
    </div>
  </div>;
}
function Workspace() {
  const { role } = useParams(); const { user } = useAuth();
  if (!['teacher', 'student'].includes(role ?? '')) return <NotFound embedded />;
  if (!user?.roles.includes(role as Role)) return <section className="empty-state"><Icon name="shield" size={40} /><h1 tabIndex={-1}>This workspace is restricted</h1><p>Your account does not have the required role.</p><Link className="btn primary" to="/workspace">Go to my workspace</Link></section>;
  if (role === 'teacher') return <TeacherDashboard />;
  return <StudentDashboard />;
}
function Account() {
  const { user, changePassword, logout } = useAuth(); const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const [confirmAll, setConfirmAll] = useState(false);
  const [mismatch, setMismatch] = useState(false);
  async function change(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const data = new FormData(event.currentTarget); setMismatch(data.get('new') !== data.get('confirm')); setError(null);
    if (data.get('new') !== data.get('confirm')) return;
    setBusy(true); try { await changePassword(String(data.get('current')), String(data.get('new'))); } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function endAll() { setBusy(true); setError(null); try { await logout(true); } catch (err) { setError(err); } finally { setBusy(false); } }
  return <><div className="page-heading"><div><span className="eyebrow">Personal settings</span><h1 tabIndex={-1}>My account</h1><p>Your identity, access and security in one place.</p></div></div>
    <div className="account-grid"><section className="panel profile-panel"><span className="avatar large">{user?.display_name.slice(0, 1).toUpperCase()}</span><h2>{user?.display_name}</h2><p className="break-text">{user?.email}</p><div className="role-badges">{user?.roles.map(role => <Badge tone="purple" key={role}>{role === 'teacher' ? 'Teacher' : 'Student'}</Badge>)}</div><div className="divider" /><h3>Account access</h3><p>Roles are managed by your project administrator. Changing your password signs you out on every device.</p><div className="quiet-note"><Icon name="shield" /><span>For your privacy, this browser keeps your session only while the page stays open.</span></div></section>
    <div><section className="panel"><div className="section-heading"><div><h2>Change password</h2><p>Choose a password with at least 12 characters.</p></div><Icon name="shield" size={25} /></div><ErrorNotice error={error} />{mismatch && <div className="notice error" role="alert">The new passwords do not match.</div>}
      <form onSubmit={change} aria-label="Change password"><fieldset disabled={busy}><PasswordField label="Current password" name="current" autoComplete="current-password" required maxLength={128} /><PasswordField label="New password" name="new" autoComplete="new-password" required minLength={12} maxLength={128} hint="12–128 characters. Your password is never trimmed." /><PasswordField label="Confirm new password" name="confirm" autoComplete="new-password" required minLength={12} maxLength={128} /><button className="btn primary" type="submit" aria-busy={busy}>{busy ? 'Please wait…' : 'Update password'}</button></fieldset></form>
    </section><section className="panel session-panel"><div><h2>Active sessions</h2><p>Sign out everywhere, including this page.</p></div>{confirmAll ? <div className="confirm-actions"><p>End all of your active sessions?</p><button className="btn secondary" onClick={() => setConfirmAll(false)} disabled={busy}>Cancel</button><button className="btn danger" onClick={() => void endAll()} disabled={busy}>Confirm sign out</button></div> : <button className="btn secondary" onClick={() => setConfirmAll(true)} disabled={busy}>Sign out everywhere</button>}</section></div></div>
  </>;
}
function NotFound({ embedded = false }: { embedded?: boolean }) {
  return <main id={embedded ? undefined : 'main'} className={embedded ? 'empty-state' : 'standalone'}>{!embedded && <Brand />}<span className="eyebrow">Page not found</span><h1 tabIndex={-1}>Let’s get you back on track.</h1><p>This page does not exist. Return to your workspace to continue.</p><Link className="btn primary" to="/workspace">Go to workspace <Icon name="arrow" /></Link></main>;
}

