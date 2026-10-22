import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';

interface IndexStatus { state: 'ready' | 'partial' | 'not_indexed'; chunks: number; indexed: number; model_available: boolean }
interface Source { citation: string; chunk_id: string; title: string; page_start: number; page_end: number; excerpt: string; similarity: number; clipped: boolean }
interface Results { status: 'sources_found' | 'insufficient_evidence'; sources: Source[]; excerpt_char_count: number }

export function SourceSearch({ materialId, onPage }: { materialId: string; onPage: (page: number) => void }) {
  const { authenticated } = useAuth(); const [status, setStatus] = useState<IndexStatus | null>(null);
  const [error, setError] = useState<unknown>(null); const [results, setResults] = useState<Results | null>(null);
  const [busy, setBusy] = useState<'index' | 'search' | null>(null); const [revision, setRevision] = useState(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController(); setStatus(null); setError(null);
    authenticated<IndexStatus>(`/rag/materials/${materialId}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setStatus(value); }).catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [materialId, revision, authenticated]);
  async function prepare() {
    if (busy) return; setBusy('index'); setError(null); setResults(null);
    const controller = new AbortController(); pending.current = controller;
    try {
      const value = await authenticated<IndexStatus>(`/rag/materials/${materialId}/index`, { method: 'POST', signal: controller.signal });
      if (!controller.signal.aborted) setStatus(value);
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(null); }
  }
  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const query = String(new FormData(event.currentTarget).get('query') ?? '').trim(); if (query.length < 2) return;
    setBusy('search'); setError(null); setResults(null); const controller = new AbortController(); pending.current = controller;
    try {
      const value = await authenticated<Results>('/rag/search', { body: { query, material_ids: [materialId] }, signal: controller.signal });
      if (!controller.signal.aborted) setResults(value);
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setBusy(null); }
  }
  return <section className="panel source-search" aria-label="Search selected material">
    <div className="section-heading"><div><span className="eyebrow">Local source search</span><h2>Find the relevant passage</h2><p>Search only the document selected in your library.</p></div><Icon name="spark" size={26} /></div>
    <ErrorNotice error={error} />
    {!status && !error && <p role="status">Checking search readiness…</p>}
    {status && <><div className="search-readiness"><Badge tone={status.state === 'ready' ? 'green' : 'purple'}>{status.state === 'ready' ? 'Ready to search' : 'Preparation needed'}</Badge><span>{status.indexed} of {status.chunks} passages indexed</span></div>
      {!status.model_available && <p className="notice warning">The local search model needs setup on this computer. See the project’s RAG setup guide. No cloud service will be used.</p>}
      {status.state !== 'ready' && <button className="btn secondary" onClick={() => void prepare()} disabled={!!busy || !status.model_available}>{busy === 'index' ? 'Preparing local search…' : 'Prepare for search'}</button>}
      <form aria-label="Search source passages" onSubmit={search}><fieldset disabled={!!busy || status.state !== 'ready' || !status.model_available}><label className="field">Topic or question<input name="query" required minLength={2} maxLength={500} placeholder="e.g. How does normalization reduce redundancy?" /></label><button type="submit" className="btn primary">{busy === 'search' ? 'Finding passages…' : 'Find passages'}</button></fieldset></form>
    </>}
    <button className="text-button" disabled={!!busy} onClick={() => { setResults(null); setRevision(n => n + 1); }}>Refresh search status</button>
    {busy && <p role="status">{busy === 'index' ? 'Creating local embeddings. This may take a few minutes.' : 'Searching your selected material locally.'} Keep this page open.</p>}
    {results?.status === 'insufficient_evidence' && <div className="notice warning" role="status">No passage met the current relevance threshold. Try a more specific topic or a different document. No answer has been generated.</div>}
    {results?.status === 'sources_found' && <div className="retrieved-sources"><h3>Retrieved source passages</h3><p className="material-hint">Similarity indicates a text match, not confidence or correctness. Review the original page.</p>{results.sources.map(source => <article className="source-chunk" key={source.chunk_id}><div className="source-heading"><span>{source.citation} · PAGE {source.page_start}{source.page_end !== source.page_start ? `–${source.page_end}` : ''}</span><small>Similarity {source.similarity.toFixed(3)}</small></div><p>{source.excerpt}</p>{source.clipped && <small>Excerpt shortened to fit the source budget.</small>}<button className="text-button" onClick={() => onPage(source.page_start)}>View source page {source.page_start}</button></article>)}</div>}
    <p className="material-hint">Semantic source retrieval is available. Generate MCQs also offers a lightweight test workflow with advisory review; test drafts cannot be published.</p>
  </section>;
}

