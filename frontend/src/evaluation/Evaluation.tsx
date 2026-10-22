import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { Badge, ErrorNotice } from '../ui';
import '../analytics/analytics.css';
import './evaluation.css';

interface Group { pair_id: string; condition: string; requested_slots: number; generated_candidates: number; retained_candidates: number; errors: Record<string, number>; verifier_decisions: Record<string, number>; math_statuses: Record<string, number>; quality: { raw: { factual_correctness: { value: number | null; status: string } } } }
interface Run { id: string; created_at: string; run: { evidence_status: string; records: unknown[]; protocol_sha256: string; dataset_sha256: string }; summary: { groups: Group[]; evidence_status: string; research_results_available: boolean; not_measured: string[] } }
const root = '/teacher/evaluation';
const names: Record<string, string> = { A: 'Topic only', B: 'Frozen RAG', C: 'RAG + verifier', D: 'Verifier + math' };

function download(value: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function Evaluation() {
  const { user } = useAuth();
  if (!user?.roles.includes('teacher')) return <section className="panel"><h1 tabIndex={-1}>Teacher access required</h1><Link to="/workspace">Go to workspace</Link></section>;
  return <Lab />;
}

function Lab() {
  const { authenticated } = useAuth(); const [items, setItems] = useState<{ id: string; created_at: string }[] | null>(null);
  const [detail, setDetail] = useState<Run | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const [refresh, setRefresh] = useState(0); const [notice, setNotice] = useState(''); const key = useRef<string | null>(null); const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => { const controller = new AbortController(); authenticated<{ items: { id: string; created_at: string }[] }>(root + '/runs', { signal: controller.signal }).then(data => { if (!controller.signal.aborted) setItems(data.items); }).catch(err => { if (!controller.signal.aborted) setError(err); }); return () => controller.abort(); }, [authenticated, refresh]);
  async function act(kind: 'run' | 'open' | 'pack', id?: string) {
    if (busy) return; setBusy(true); setError(null); setNotice(''); const controller = new AbortController(); pending.current = controller;
    try {
      if (kind === 'pack' && detail) {
        const pack = await authenticated(root + `/runs/${detail.id}/review-pack`, { signal: controller.signal });
        if (!controller.signal.aborted) { download(pack, 'operator-review-bundle.json'); setNotice('Operator bundle downloaded. Give reviewers only the reviewer items and blank ratings template; keep the allocation map private.'); }
      } else {
        if (kind === 'run') key.current ??= crypto.randomUUID(); else setDetail(null);
        const result = await authenticated<Run>(root + `/runs${kind === 'open' ? '/' + id : ''}`, { signal: controller.signal, ...(kind === 'run' ? { body: { idempotency_key: key.current } } : {}) });
        if (!controller.signal.aborted) { setDetail(result); if (kind === 'run') { key.current = null; setRefresh(n => n + 1); setNotice('Synthetic smoke check saved. No model ran and no classroom question was created.'); } }
      }
    } catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <><div className="page-heading"><div><span className="eyebrow">Measure before making claims</span><h1 tabIndex={-1}>Evaluation lab</h1><p>Reproducible comparisons, independent review and clear evidence boundaries.</p></div><Badge tone="purple">Research tooling</Badge></div>
    <ErrorNotice error={error} />{notice && <div className="notice success" role="status">{notice}</div>}
    <section className="panel evaluation-intro"><div><h2>Test the measurement workflow</h2><p>This page runs a small synthetic smoke check. It exercises the evaluation process without LLM inference. Its counts and timings describe software behavior; AI correctness and educational benefits remain <strong>To be evaluated</strong>.</p><button className="btn primary" disabled={busy || (items?.length ?? 0) >= 20} onClick={() => void act('run')}>{busy ? 'Please wait…' : 'Run synthetic smoke check'}</button><p className="muted">Up to 20 saved smoke runs per teacher. Run retries are safe.</p></div><div className="evaluation-flow">{Object.entries(names).map(([letter, title]) => <div key={letter}><span>{letter}</span><strong>{title}</strong></div>)}</div></section>
    <section className="panel"><h2>Saved checks</h2>{items?.length === 0 && <p>No evaluation runs yet. No research results have been assumed.</p>}{!items && !error && <p role="status">Loading saved checks…</p>}<div className="evaluation-runs">{items?.map(item => <button className="btn secondary" key={item.id} disabled={busy} aria-pressed={detail?.id === item.id} onClick={() => void act('open', item.id)}>Open check {item.id.slice(0, 8)} · {new Date(item.created_at).toLocaleString()}</button>)}</div></section>
    {detail && <section className="panel"><div className="section-heading"><div><h2>Matched comparison</h2><p>{detail.run.evidence_status}</p></div><Badge tone="purple">Not research results</Badge></div><p>A and B generate separately with matched inputs and seeds. C reviews the exact B candidate; D checks that same candidate mathematically. Rejections are retained in the evidence. Nothing here can be published as an assessment.</p><div className="analytics-table" role="region" aria-label="Evaluation conditions" tabIndex={0}><table><thead><tr><th>Condition</th><th>Requested</th><th>Generated</th><th>Retained (synthetic)</th><th>AI correctness</th></tr></thead><tbody>{detail.summary.groups.map(group => <tr key={group.pair_id + group.condition}><td><strong>{group.condition} · {names[group.condition]}</strong><small>{group.pair_id}</small></td><td>{group.requested_slots}</td><td>{group.generated_candidates}</td><td>{group.retained_candidates}</td><td>To be evaluated</td></tr>)}</tbody></table></div><p>The synthetic verifier intentionally passes a wrong numerical key, so condition D can exercise rejection. These fixture outcomes do not measure verifier reliability.</p><div className="analytics-toolbar"><button className="btn secondary" onClick={() => download(detail.run, 'evaluation-run.json')}>Download run evidence</button><button className="btn secondary" disabled={busy} onClick={() => void act('pack')}>Download review bundle</button></div><details><summary>Reproducibility and missing measurements</summary><p className="evaluation-hash">Dataset hash: {detail.run.dataset_sha256}<br />Protocol hash: {detail.run.protocol_sha256}</p><p>Not measured: {detail.summary.not_measured.join(', ')}.</p><p>Local research runs use the separate operator command-line harness after hardware validation. Different model checkpoints are not assumed available. The website cannot start real inference.</p></details></section>}
    <section className="panel"><h2>Independent review protocol</h2><ol><li>Freeze authorized source documents, retrieval snapshots, prompts and model configuration on a development split.</li><li>Run the unchanged protocol on held-out documents. Keep model-pair comparisons separate.</li><li>Give two independent reviewers the blinded items and rubric. Use a separate adjudicator for disagreements.</li><li>Report raw and retained quality, rating coverage, failure counts, yield and uncertainty. Never substitute the verifier’s opinion for independent labels.</li></ol><p>Source snippets may make complete blinding impossible; only allocation labels are hidden. Downloaded operator bundles contain the private allocation map.</p></section>
    <StudyExport />
  </>;
}

function StudyExport() {
  const { authenticated } = useAuth(); const [page, setPage] = useState<{ items: { id: string; title: string }[]; total: number } | null>(null); const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]); const [consent, setConsent] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState(''); const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => { const controller = new AbortController(); setPage(null); authenticated<{ items: { id: string; title: string }[]; total: number }>(`/teacher/assessments?offset=${offset}&limit=6`, { signal: controller.signal }).then(data => { if (!controller.signal.aborted) setPage(data); }).catch(err => { if (!controller.signal.aborted) setError(err); }); return () => controller.abort(); }, [authenticated, offset]);
  async function exportStudy() {
    if (!consent || !selected.length || busy) return; setBusy(true); setError(null); setNotice(''); const controller = new AbortController(); pending.current = controller;
    try { const data = await authenticated<{ events: unknown[] }>(root + '/adaptive-export', { body: { assessment_ids: selected, consent_confirmed: true }, signal: controller.signal }); if (!controller.signal.aborted) { download(data, 'private-adaptive-events.json'); setNotice(`Downloaded ${data.events.length} eligible events. This is observational evidence, not proof of learning gains.`); } } catch (err) { if (!controller.signal.aborted) setError(err); } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="panel"><h2>Separate adaptive-policy export</h2><p>Export released first-exposure evidence from up to eight owned classroom assessments. Names, emails, comments, question text and event timestamps are omitted. Pseudonyms are fresh for each export; keep the file private.</p><ErrorNotice error={error} />{notice && <p role="status">{notice}</p>}<fieldset disabled={busy}>{page?.total === 0 && <p>No classroom assessments available.</p>}{page?.items.map(item => <label className="evaluation-check" key={item.id}><input type="checkbox" checked={selected.includes(item.id)} disabled={!selected.includes(item.id) && selected.length >= 8} onChange={event => { setSelected(old => event.target.checked ? [...old, item.id] : old.filter(id => id !== item.id)); setConsent(false); }} />{item.title}</label>)}{page && page.total > 6 && <div className="analytics-toolbar"><button className="btn secondary" disabled={offset === 0} onClick={() => setOffset(n => n - 6)}>Previous assessments</button><button className="btn secondary" disabled={offset + 6 >= page.total} onClick={() => setOffset(n => n + 6)}>Next assessments</button></div>}<p>{selected.length} assessment(s) selected across pages.</p><label className="evaluation-check"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />I confirm permission and participant consent for this research export.</label><button className="btn secondary" disabled={busy || !consent || !selected.length} onClick={() => void exportStudy()}>{busy ? 'Preparing export…' : 'Download private study events'}</button></fieldset><p>Offline replay compares policy recommendations before each recorded answer. It cannot predict responses to unasked questions or establish learning improvement. Real learner studies require a separate study design.</p></section>;
}
