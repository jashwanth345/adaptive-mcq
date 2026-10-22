import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError } from '../api';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import './generator.css';
import { ReviewPanel } from './ReviewPanel';
import { ValidationPanel } from './ValidationPanel';

interface Status { mode: 'mock' | 'disabled' | 'ollama'; ready: boolean; model: string; selection_status: string; error_code: string | null; hardware: { available_ram_gib?: number; ram_gib?: number } }
interface Material { id: string; title: string }
interface Summary { id: string; topic: string; stem: string; mode: string; created_at: string }
interface Draft extends Summary { options: string[]; correct_option: number; explanation: string; difficulty: string; cognitive_level: string; status: 'unverified'; model: string; retrieval: string; evidence_quote: string; source: { material_id: string; citation: string; title: string; page_start: number; page_end: number } }
interface Page<T> { items: T[]; total: number }
interface BatchItem { draft?: Draft; generatedKey: string; reviewKey: string; validationKey: string; reviewed?: string; validated?: boolean }
interface Batch { fingerprint: string; id: string; items: BatchItem[]; next: number }

export function Drafts() {
  const { authenticated, user } = useAuth(); const [params] = useSearchParams();
  const [status, setStatus] = useState<Status | null>(null); const [materials, setMaterials] = useState<Material[]>([]);
  const [material, setMaterial] = useState(params.get('material') ?? ''); const [history, setHistory] = useState<Page<Summary> | null>(null);
  const [offset, setOffset] = useState(0); const [revision, setRevision] = useState(0); const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const [count, setCount] = useState(10); const [progress, setProgress] = useState('');
  const [batchItems, setBatchItems] = useState<BatchItem[]>([]);
  const batch = useRef<Batch | null>(null); const stop = useRef(false);
  const pending = useRef<AbortController | null>(null); const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController(); setError(null);
    async function load() {
      // Local library is capped at 50 documents; fetch its bounded pages.
      const [readiness, first, second, third, recent] = await Promise.all([
        authenticated<Status>('/generator/status', { signal: controller.signal }),
        authenticated<Page<Material>>('/materials?offset=0&limit=24', { signal: controller.signal }),
        authenticated<Page<Material>>('/materials?offset=24&limit=24', { signal: controller.signal }),
        authenticated<Page<Material>>('/materials?offset=48&limit=24', { signal: controller.signal }),
        authenticated<Page<Summary>>(`/generator/drafts?offset=${offset}&limit=6`, { signal: controller.signal }),
      ]);
      if (controller.signal.aborted) return;
      setStatus(readiness); setMaterials([...first.items, ...second.items, ...third.items]); setHistory(recent);
    }
    void load().catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [authenticated, offset, revision]);
  useEffect(() => {
    if (busy || status?.mode !== 'ollama' || status.ready) return;
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      void authenticated<Status>('/generator/status', { signal: controller.signal })
        .then(next => { if (!controller.signal.aborted) setStatus(next); })
        .catch(() => { /* Keep the last actionable readiness message. */ });
    }, 15000);
    return () => { window.clearInterval(timer); controller.abort(); };
  }, [authenticated, busy, status?.mode, status?.ready]);
  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || !status?.ready || !material) return;
    const form = new FormData(event.currentTarget);
    const body = { material_ids: [material], topic: String(form.get('topic')).trim(), difficulty: String(form.get('difficulty')), cognitive_level: String(form.get('cognitive')) };
    if (status.mode === 'ollama') {
      await generateBatch(body); return;
    }
    const fingerprint = JSON.stringify(body);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    const controller = new AbortController(); pending.current = controller; setBusy(true); setError(null); setDraft(null);
    try {
      const saved = await authenticated<Draft>('/generator/drafts', { body: { ...body, idempotency_key: retry.current.key }, signal: controller.signal });
      if (!controller.signal.aborted) { setDraft(saved); retry.current = null; setOffset(0); setRevision(n => n + 1); }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function generateBatch(body: { material_ids: string[]; topic: string; difficulty: string; cognitive_level: string }) {
    if (!Number.isInteger(count) || count < 10 || count > 30) return;
    const fingerprint = JSON.stringify({ ...body, count });
    if (batch.current?.fingerprint !== fingerprint || batch.current.next === count) {
      batch.current = { fingerprint, id: crypto.randomUUID(), next: 0, items: Array.from({ length: count }, () => ({ generatedKey: crypto.randomUUID(), reviewKey: crypto.randomUUID(), validationKey: crypto.randomUUID() })) };
    }
    const active = batch.current;
    const controller = new AbortController(); pending.current = controller; stop.current = false;
    setBusy(true); setError(null); setBatchItems([...active.items]);
    try {
      setProgress('Checking the local generator and verifier…');
      const generator = await authenticated<Status>('/generator/status', { signal: controller.signal });
      const verifier = await authenticated<Status>('/verifier/status', { signal: controller.signal });
      if (generator.mode !== 'ollama' || verifier.mode !== 'ollama') throw new ApiError(409, 'GENERATOR_REAL_REQUIRED');
      if (!generator.ready || !verifier.ready) throw new ApiError(503, generator.error_code ?? verifier.error_code ?? 'GENERATOR_OFFLINE');
      setProgress('Preparing this PDF for local semantic search…');
      await authenticated(`/rag/materials/${body.material_ids[0]}/index`, { method: 'POST', signal: controller.signal });
      for (let i = active.next; i < count; i++) {
        if (stop.current || controller.signal.aborted) break;
        const item = active.items[i];
        setProgress(`Question ${i + 1} of ${count}: retrieving evidence and generating…`);
        if (!item.draft) item.draft = await authenticated<Draft>('/generator/drafts', { body: { ...body, batch_id: active.id, batch_count: count, batch_index: i, idempotency_key: item.generatedKey }, signal: controller.signal });
        if (controller.signal.aborted) return;
        setDraft(item.draft); setBatchItems([...active.items]);
        setProgress(`Question ${i + 1} of ${count}: verifying the answer and options…`);
        if (!item.reviewed) {
          const review = await authenticated<{ recommendation: string; ai_executed: boolean }>(`/verifier/drafts/${item.draft.id}/reports`, { body: { idempotency_key: item.reviewKey }, signal: controller.signal });
          if (!review.ai_executed) throw new ApiError(409, 'GENERATOR_REAL_REQUIRED');
          item.reviewed = review.recommendation;
        }
        setProgress(`Question ${i + 1} of ${count}: checking duplicates and answerability…`);
        if (item.validated === undefined) {
          const validation = await authenticated<{ technical_pass: boolean }>(`/validation/drafts/${item.draft.id}/reports`, { body: { idempotency_key: item.validationKey }, signal: controller.signal });
          item.validated = validation.technical_pass;
        }
        active.next = i + 1; setBatchItems([...active.items]);
      }
      if (!controller.signal.aborted) setProgress(active.next === count ? `${count} drafts processed. Review the checks below; failed questions are not approved MCQs.` : `Paused after ${active.next} of ${count}. Submit the same settings to resume.`);
    } catch (err) {
      if (!controller.signal.aborted) { setError(err); setProgress(`Stopped at question ${active.next + 1} of ${count}. Saved drafts are retained. Retry the same settings to resume without duplicating saves.`); }
    } finally {
      if (!controller.signal.aborted) { setBusy(false); setBatchItems([...active.items]); setOffset(0); setRevision(n => n + 1); }
    }
  }
  async function open(id: string) {
    if (busy) return; setBusy(true); setError(null); setDraft(null);
    const controller = new AbortController(); pending.current = controller;
    try { const saved = await authenticated<Draft>(`/generator/drafts/${id}`, { signal: controller.signal }); if (!controller.signal.aborted) setDraft(saved); }
    catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <>
    <div className="page-heading"><div><span className="eyebrow">From source to question</span><h1 tabIndex={-1}>Generate MCQs</h1><p>Create a private draft, inspect its evidence and keep your work in one place.</p></div><Badge tone="purple">Unverified drafts</Badge></div>
    <div className="draft-pipeline" aria-label="Draft workflow"><span><Icon name="book" /> Your PDF</span><span>→</span><span><Icon name="spark" /> {status?.mode === 'mock' ? 'Test generator' : 'Local generator'}</span><span>→</span><span><Icon name="layers" /> Private draft</span><span className="draft-future">Advisory review</span></div>
    <ErrorNotice error={error} />
    {!status && !error && <p role="status">Loading your draft workspace…</p>}
    <div className="draft-grid"><div><section className="panel">
      <div className="section-heading"><div><h2>Create your question set</h2><p>Select 10–30 questions. Each question is generated and checked sequentially to limit memory use.</p></div><Icon name="spark" size={26} /></div>
      {status?.mode === 'mock' && <div className="notice warning"><strong>Test mode — no AI inference</strong><p>Real MCQ generation is not enabled on this computer. The test button below creates one placeholder draft only. It does not produce educational questions or run semantic RAG. Uploading a PDF alone does not enable the LLM.</p><p>To generate 10–30 real questions, a prepared local model and enough free RAM are required. No cloud service is used.</p></div>}
      {status?.mode === 'ollama' && <p className="notice warning">Local AI mode. The selected PDF is prepared for semantic search automatically. Generation, answer verification and validation run one after another. Review all results before using them; model agreement does not guarantee correctness.</p>}
      {status?.mode === 'disabled' && <p className="notice warning">Draft generation is disabled in the local configuration.</p>}
      {status?.error_code && <ErrorNotice error={new ApiError(503, status.error_code)} />}
      {status?.mode === 'ollama' && !status.ready && <p className="notice warning" role="status">Generation is waiting for the local model to be ready. {status.error_code === 'GENERATOR_LOW_MEMORY' && <>Free RAM: {status.hardware.available_ram_gib ?? 'unknown'} GiB; at least 1.5 GiB is required. Close unused applications. </>}Readiness is checked again every 15 seconds. You can choose your PDF and settings now.</p>}
      <form aria-label="Create private draft" onSubmit={generate}><fieldset disabled={busy || !status}>
        <label className="field">Source document<select value={material} onChange={event => setMaterial(event.target.value)} required><option value="">Choose a processed PDF</option>{materials.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
        <label className="field">Draft topic<input name="topic" required minLength={2} maxLength={100} placeholder="e.g. normalization" /></label>
        <label className="field">Number of questions<select value={count} onChange={event => setCount(Number(event.target.value))}>{Array.from({ length: 21 }, (_, i) => i + 10).map(n => <option key={n} value={n}>{n} questions</option>)}</select></label>
        <div className="draft-settings"><label className="field">Target difficulty<select name="difficulty" defaultValue="easy"><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select></label><label className="field">Target cognitive level<select name="cognitive" defaultValue="understand"><option value="remember">Remember</option><option value="understand">Understand</option></select></label></div>
        <p className="material-hint">Targets are saved as preferences. Test mode does not adapt question difficulty or cognitive level.</p>
        <button className="btn primary" type="submit" disabled={!material || !status?.ready || status?.mode !== 'ollama'} aria-busy={busy}>{busy ? 'Please wait…' : `Generate ${count} MCQs`}</button>
        {status?.mode === 'mock' && <button className="btn secondary" type="submit" disabled={!material}>Create test draft</button>}
      </fieldset></form>
      {busy && status?.mode === 'ollama' && <button className="btn secondary" onClick={() => { stop.current = true; setProgress('Pausing after the current question is saved and checked…'); }}>Pause after this question</button>}
      {progress && <p role="status">{progress}</p>}
      <Link className="text-button" to="/materials">Upload or prepare a PDF</Link>
      <button className="text-button" disabled={busy} onClick={() => setRevision(n => n + 1)}>Refresh draft workspace</button>
      {busy && <p role="status">Working locally. Keep this page open; your draft will be saved privately.</p>}
      {status && <details className="draft-hardware"><summary>Local model readiness</summary><p>{status.selection_status}</p><p>{status.hardware.available_ram_gib ?? 'Unknown'} GiB available / {status.hardware.ram_gib ?? 'Unknown'} GiB total RAM at last refresh.</p><p>Configured candidate: {status.model}. Test mode does not load it. No cloud fallback.</p></details>}
    </section>
    {batchItems.some(item => item.draft) && <section className="panel draft-history" aria-label="Generated question set"><h2>Your question set</h2><p>{batchItems.filter(item => item.draft).length} saved · {batchItems.filter(item => item.reviewed === 'PASS' && item.validated).length} passed these checks. Teacher approval is separate.</p>{batchItems.map((item, i) => item.draft && <button key={item.generatedKey} className="draft-item" disabled={busy} onClick={() => void open(item.draft!.id)}><strong>Question {i + 1}: {item.draft.stem}</strong><span>{!item.reviewed ? 'Verification pending' : item.reviewed !== 'PASS' ? `Verifier: ${item.reviewed}` : item.validated === undefined ? 'Validation pending' : item.validated ? 'Checks passed · not approved' : 'Validation blocked'}</span></button>)}</section>}
    <section className="panel draft-history"><div className="section-heading"><div><h2>Saved drafts</h2><p>{history?.total ?? 0} private draft{history?.total === 1 ? '' : 's'}</p></div><Icon name="layers" /></div>
      {history?.total === 0 && <p>Your saved drafts will appear here.</p>}
      {history?.items.map(item => <button className="draft-item" aria-label={`Open ${item.mode === 'mock' ? 'test' : 'AI'} draft: ${item.topic}`} key={item.id} disabled={busy} onClick={() => void open(item.id)} aria-pressed={draft?.id === item.id}><strong>{item.topic}</strong><span>{item.mode === 'mock' ? 'Test draft' : 'AI draft'} · Unverified</span><small>{new Date(item.created_at).toLocaleDateString()}</small></button>)}
      {history && history.total > 6 && <div className="material-pagination"><button className="btn secondary" disabled={!offset || busy} onClick={() => setOffset(n => n - 6)}>Previous drafts</button><span>{Math.floor(offset / 6) + 1} / {Math.ceil(history.total / 6)}</span><button className="btn secondary" disabled={offset + 6 >= history.total || busy} onClick={() => setOffset(n => n + 6)}>Next drafts</button></div>}
    </section></div>
    <section className="panel draft-preview" aria-label="Private draft preview">
      <span className="eyebrow">Inspect the proposed question</span><h2>Draft preview</h2>
      {!draft && <div className="material-empty"><Icon name="layers" size={40} /><h3>A question begins with evidence</h3><p>Create a draft or open a saved one to run a private review. These drafts cannot be published or used for scoring.</p></div>}
      {draft && <><Badge tone="purple">{draft.mode === 'mock' ? 'Test draft — not AI-generated' : 'AI draft — unverified'}</Badge><h3 className="draft-stem">{draft.stem}</h3><ol className="draft-options" type="A">{draft.options.map((option, n) => <li key={n} className={n === draft.correct_option ? 'proposed' : ''}>{option}{n === draft.correct_option && <small>Proposed answer · unverified</small>}</li>)}</ol>
        <h3>Proposed explanation</h3><p>{draft.explanation}</p><div className="draft-evidence"><span className="eyebrow">{draft.source.citation} · Page {draft.source.page_start}{draft.source.page_end !== draft.source.page_start ? `–${draft.source.page_end}` : ''}</span><h3>{draft.source.title}</h3><blockquote>{draft.evidence_quote}</blockquote><p>Exact source text is recorded. This does not prove answer correctness.</p><Link className="text-button" to="/materials">Open study materials</Link></div>
        <p className="material-hint">Requested: {draft.difficulty} · {draft.cognitive_level}. {draft.retrieval === 'keyword_test' ? 'Test keyword selection' : 'Semantic source retrieval'}. Saved privately; no assessment created.</p>
        <fieldset disabled={busy}>
          <ReviewPanel key={`${draft.id}-${batchItems.filter(item => item.validated !== undefined).length}`} versionId={draft.id} draftMode={draft.mode} />
          <ValidationPanel key={`validation-${draft.id}-${batchItems.filter(item => item.validated !== undefined).length}`} versionId={draft.id} />
        </fieldset>
        {user?.roles.includes('teacher') && <Link className="btn secondary" to={`/teacher-review?version=${draft.id}`}>Open teacher review</Link>}
      </>}
    </section></div>
  </>;
}


