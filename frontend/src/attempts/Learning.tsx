import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import type { AttemptData } from './Attempt';
import './attempts.css';

interface Topic { topic_id: string; topic: string; observations: number; performance_index: number | null; recommended_difficulty: string; reason: string; levels: { difficulty: string; observations: number; covered: boolean; estimate: number | null }[] }
interface LearningData { policy: { version: string; minimum_evidence: number; decay: number; promote_at: number; demote_at: number; recent_window: number; weights: number[] }; policy_status: string; topics: Topic[]; eligible_observations: number; retained_evidence_count: number; recommendation: { version_id: string; topic: string; difficulty: string; reason: string } | null; scope: string }

export function Learning() {
  const { user } = useAuth();
  if (!user?.roles.includes('student')) return <section className="panel"><h1 tabIndex={-1}>Student access required</h1><Link to="/workspace">Go to workspace</Link></section>;
  return <LearningWorkspace />;
}

function LearningWorkspace() {
  const { authenticated } = useAuth(); const navigate = useNavigate(); const [data, setData] = useState<LearningData | null>(null); const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false); const retry = useRef<{ id: string; key: string } | null>(null); const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => { const controller = new AbortController(); setError(null); authenticated<LearningData>('/student/learning', { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setData(value); }).catch(err => { if (!controller.signal.aborted) setError(err); }); return () => controller.abort(); }, [authenticated, refresh]);
  async function practice() {
    if (!data?.recommendation || busy) return; const id = data.recommendation.version_id;
    if (retry.current?.id !== id) retry.current = { id, key: crypto.randomUUID() };
    const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null);
    try { const attempt = await authenticated<AttemptData>('/student/practice/start', { body: { version_id: id, idempotency_key: retry.current.key }, signal: controller.signal }); if (!controller.signal.aborted) navigate(`/attempts/${attempt.id}`); }
    catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <><div className="page-heading"><div><span className="eyebrow">Evidence, then the next step</span><h1 tabIndex={-1}>My learning</h1><p>Topic progress from eligible responses, with clear limits and a next practice suggestion.</p></div><Badge tone="purple">Candidate adaptive policy</Badge></div><ErrorNotice error={error} />
    <div className="attempt-toolbar"><button className="btn secondary" disabled={busy} onClick={() => setRefresh(n => n + 1)}>Refresh learning profile</button><Link to="/workspace/student">Attempt history</Link><Link to="/drafts">Prepare private questions</Link></div>
    {data && <><div className="learning-summary"><section className="panel"><Icon name="chart" size={26} /><h2>{data.eligible_observations} eligible responses</h2><p>First exposure, submitted and released. Skips, repeated items, expired attempts and quarantined content are excluded.</p></section><section className="panel"><h2>Your next practice</h2>{data.recommendation ? <><h3>{data.recommendation.topic}</h3><Badge tone="green">{data.recommendation.difficulty}</Badge><p>{data.recommendation.reason}</p><button className="btn primary" disabled={busy} onClick={() => void practice()}>{busy ? 'Opening practice…' : 'Start suggested practice'}</button></> : <><p>No eligible unseen private question is ready.</p><p>Prepare your own material and complete real verification and validation in Generate MCQs. Test-generated content cannot be used for scored practice.</p></>}</section></div>
      {data.topics.length === 0 && <section className="panel"><h2>Insufficient evidence</h2><p>Complete an eligible assessment and wait for its results to be released. No mastery percentage is assumed for a new learner.</p></section>}
      <div className="learning-topics">{data.topics.map(topic => <section className="panel" key={topic.topic_id}><div className="section-heading"><h2>{topic.topic}</h2><Badge tone="purple">{topic.recommended_difficulty} next</Badge></div><div className="learning-index"><strong>{topic.performance_index == null ? 'Insufficient evidence' : `${topic.performance_index.toFixed(1)}%`}</strong><span>Provisional performance index · {topic.observations} eligible responses</span></div>{topic.performance_index != null && <progress max={100} value={topic.performance_index} aria-label={`${topic.topic} performance index`} />}<p>{topic.reason}</p><div className="learning-levels">{topic.levels.map(level => <span key={level.difficulty}><strong>{level.difficulty}</strong>{level.observations} responses · {level.covered ? 'Covered' : 'More evidence needed'}</span>)}</div></section>)}</div>
      <section className="panel learning-policy"><h2>How to read this profile</h2><p>A performance indicator, not a validated measure of knowledge. Fixed classroom assessments do not change difficulty. Response time does not penalize your profile.</p><details><summary>Policy assumptions — to be evaluated</summary><p>{data.policy.version}: at least {data.policy.minimum_evidence} observations per covered level; decay {data.policy.decay}; promotion threshold {data.policy.promote_at}; demotion threshold {data.policy.demote_at}; recent window {data.policy.recent_window}; difficulty weights {data.policy.weights.join(', ')}. Symmetric prior: one correct and one incorrect observation. At most one level change per eligible answer.</p><p>{data.scope}</p></details></section>
    </>}{!data && !error && <p role="status">Loading eligible learning evidence…</p>}
  </>;
}
