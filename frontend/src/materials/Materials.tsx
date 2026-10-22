import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../api';
import { useAuth } from '../auth';
import { Badge, ErrorNotice, Icon } from '../ui';
import './materials.css';
import { SourceSearch } from './SourceSearch';

interface Material { id: string; title: string; created_at: string; page_count: number; byte_size: number; chunk_count: number }
interface Library { items: Material[]; total: number; offset: number; limit: number }
interface Preview extends Material { page: number; chunks: { ordinal: number; content: string }[]; empty_pages: number[]; ocr_pages?: number[] }

export function Materials() {
  const { authenticated } = useAuth();
  const [library, setLibrary] = useState<Library | null>(null);
  const [error, setError] = useState<unknown>(null); const [uploadError, setUploadError] = useState<unknown>(null);
  const [offset, setOffset] = useState(0); const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<string | null>(null); const [page, setPage] = useState(1);
  const [preview, setPreview] = useState<Preview | null>(null); const [previewError, setPreviewError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false); const [notice, setNotice] = useState('');
  const [chosen, setChosen] = useState<File | null>(null); const [dragging, setDragging] = useState(false);
  const titleInput = useRef<HTMLInputElement>(null);
  const upload = useRef<AbortController | null>(null);
  useEffect(() => () => upload.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController(); setLibrary(null); setError(null);
    authenticated<Library>(`/materials?offset=${offset}&limit=6`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setLibrary(value); }).catch(err => { if (!controller.signal.aborted) setError(err); });
    return () => controller.abort();
  }, [authenticated, offset, revision]);
  useEffect(() => {
    const controller = new AbortController(); setPreview(null); setPreviewError(null);
    if (selected) authenticated<Preview>(`/materials/${selected}?page=${page}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setPreview(value); }).catch(err => { if (!controller.signal.aborted) setPreviewError(err); });
    return () => controller.abort();
  }, [authenticated, selected, page, revision]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const form = event.currentTarget; const data = new FormData(form);
    const file = chosen;
    setUploadError(null); setNotice('');
    if (!file?.size || !file.name.toLowerCase().endsWith('.pdf')) { setUploadError(new ApiError(415, 'PDF_REQUIRED')); return; }
    if (file.size > 5 * 1024 * 1024) { setUploadError(new ApiError(413, 'PDF_TOO_LARGE')); return; }
    const title = String(data.get('title') ?? '').trim(); if (!title) return;
    const controller = new AbortController(); upload.current = controller; setBusy(true);
    try {
      const result = await authenticated<{ id: string; reused: boolean }>(`/materials?title=${encodeURIComponent(title)}`, { body: file, signal: controller.signal });
      if (controller.signal.aborted) return;
      setNotice(result.reused ? 'This PDF is already in your library. Opened the existing material.' : 'PDF saved. Extracted text is ready to review.');
      form.reset(); setChosen(null); setOffset(0); setSelected(result.id); setPage(1); setRevision(n => n + 1);
    } catch (err) { if (!controller.signal.aborted) { setUploadError(err); setRevision(n => n + 1); } }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  function choose(file?: File) {
    if (busy) return;
    setUploadError(null); setNotice(''); setChosen(null);
    if (!file) return;
    if (!file.size || !file.name.toLowerCase().endsWith('.pdf')) { setUploadError(new ApiError(415, 'PDF_REQUIRED')); return; }
    if (file.size > 5 * 1024 * 1024) { setUploadError(new ApiError(413, 'PDF_TOO_LARGE')); return; }
    setChosen(file);
    if (titleInput.current && !titleInput.current.value.trim()) titleInput.current.value = file.name.replace(/\.pdf$/i, '').slice(0, 250);
  }
  return <>
    <div className="page-heading"><div><span className="eyebrow">Your source material</span><h1 tabIndex={-1}>Study materials</h1><p>A private library for the ideas you want to learn and assess.</p></div><Badge tone="green">Stored locally</Badge></div>
    <div className="materials-grid"><div>
      <section className="panel material-upload"><div className="section-heading"><div><h2>Upload study material</h2><p>PDF only · up to 5 MiB · 100 pages</p></div><Icon name="book" size={28} /></div>
        <form onSubmit={submit} aria-label="Upload study PDF"><fieldset disabled={busy}>
          <label className={`pdf-picker ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); if (!busy) choose(event.dataTransfer.files[0]); }}>
            <span className="upload-symbol"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M7 18H5a4 4 0 0 1-1-8 7 7 0 0 1 14-1 4.5 4.5 0 0 1 1 9h-2M12 21V11m-4 4 4-4 4 4" /></svg></span>
            <strong>Drag & drop your PDF here</strong><span>or <b>click to choose a file</b></span><small>PDF · Maximum 5 MiB</small>
            <input name="pdf" type="file" accept=".pdf,application/pdf" required={!chosen} aria-label="Choose PDF" aria-describedby="pdf-hint" onChange={event => choose(event.target.files?.[0])} />
          </label>
          {chosen && <div className="chosen-file" role="status"><span className="pdf-file-icon">PDF</span><div><strong>{chosen.name}</strong><small>{(chosen.size / 1024).toFixed(1)} KiB · Ready to process</small></div><Icon name="check" /></div>}
          <label className="field">Material title<input ref={titleInput} name="title" required maxLength={250} placeholder="e.g. Database normalization notes" /></label>
          <p id="pdf-hint" className="material-hint">Text PDFs are recommended. On Windows, scans use installed offline OCR (up to 10 scanned pages). Password-protected PDFs are not supported.</p>
          <ErrorNotice error={uploadError} /><button type="submit" className="btn primary" aria-busy={busy}>{busy ? 'Uploading & extracting…' : 'Upload and process'}</button>
        </fieldset></form>
        {busy && <div className="processing-status" role="status"><span className="processing-spinner" /><span>Reading your PDF and recognizing scanned pages when needed. Keep this page open; processing may take up to 90 seconds.</span></div>}
        {notice && <p className="notice success" role="status">{notice}</p>}
        <div className="quiet-note"><Icon name="shield" /><span>Only your account can access these materials. Local source search is available below after selecting a document. Private test drafts are available under Generate MCQs. Real AI quality awaits hardware validation.</span></div>
      </section>
      <section className="panel material-library"><div className="section-heading"><div><h2>My library</h2><p>{library ? `${library.total} processed document${library.total === 1 ? '' : 's'}` : 'Your saved documents'}</p></div><button className="btn secondary" onClick={() => setRevision(n => n + 1)} disabled={busy}>Refresh library</button></div>
        <ErrorNotice error={error} />{!library && !error && <p role="status">Loading materials…</p>}
        {library?.total === 0 && <div className="material-empty"><Icon name="layers" size={30} /><h3>Your library starts here</h3><p>Upload a PDF to inspect its extracted text, page by page.</p></div>}
        {library?.items.map(item => <button type="button" className={`material-item ${selected === item.id ? 'selected' : ''}`} aria-pressed={selected === item.id} key={item.id} onClick={() => { setSelected(item.id); setPage(1); }}><Icon name="book" /><span><strong>{item.title}</strong><small>{item.page_count} pages · {(item.byte_size / 1024).toFixed(1)} KiB · Text extracted</small></span><Icon name="arrow" /></button>)}
        {library && library.total > 6 && <div className="material-pagination"><button className="btn secondary" disabled={!offset} onClick={() => setOffset(n => n - 6)}>Previous documents</button><span>{Math.floor(offset / 6) + 1} / {Math.ceil(library.total / 6)}</span><button className="btn secondary" disabled={offset + 6 >= library.total} onClick={() => setOffset(n => n + 6)}>Next documents</button></div>}
      </section>
    </div><section className="panel material-preview" aria-label="Extracted text preview"><span className="eyebrow">Source preview</span><h2>{preview?.title ?? 'Explore your document'}</h2>
      {!selected && <div className="material-empty"><Icon name="book" size={38} /><h3>Every question begins with a source</h3><p>Select a saved document to check the extracted text and its original page numbers.</p></div>}
      <ErrorNotice error={previewError} />{Boolean(previewError) && <button className="btn secondary" onClick={() => setRevision(n => n + 1)}>Retry preview</button>}
      {selected && !preview && !previewError && <p role="status">Loading page…</p>}
      {preview && <><div className="material-pagination"><button className="btn secondary" disabled={page === 1} onClick={() => setPage(n => n - 1)}>Previous page</button><strong>Page {page} of {preview.page_count}</strong><button className="btn secondary" disabled={page === preview.page_count} onClick={() => setPage(n => n + 1)}>Next page</button></div>
        {Boolean(preview.ocr_pages?.length) && <p className="notice warning">Scanned text recognized on pages {preview.ocr_pages?.join(', ')}. Check names, reading order and equations against the original PDF before generating questions.</p>}
        {preview.empty_pages.length > 0 && <p className="notice warning">Pages without extractable text: {preview.empty_pages.join(', ')}. They may be blank or unreadable scans.</p>}
        <p className="material-hint">Extracted passages can overlap. Review reading order and equations against the original PDF.</p>
        {preview.chunks.length === 0 ? <p>No extractable text on this page.</p> : preview.chunks.map(chunk => <article className="source-chunk" key={chunk.ordinal}><span>PASSAGE {chunk.ordinal + 1} · PAGE {page}</span><p>{chunk.content}</p></article>)}
        <p className="material-hint">{preview.chunk_count} passages retained with page references. Prepare this document for local search below. Private test drafts are available under Generate MCQs. Real AI quality awaits hardware validation.</p></>}
    </section></div>
    {selected && <SourceSearch key={selected} materialId={selected} onPage={setPage} />}
    {selected && <div className="panel"><h2>Continue to a private draft</h2><p>Open Generate MCQs with this document selected. Test drafts are labelled and cannot be published.</p><Link className="btn primary" to={`/drafts?material=${selected}`}>Continue to questions</Link></div>}
  </>;
}

