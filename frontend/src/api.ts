export type Role = 'teacher' | 'student';
export interface User { id: string; email: string; display_name: string; roles: Role[]; created_at: string }
export interface Login { access_token: string; token_type: 'bearer'; expires_in: number; user: User }
export class ApiError extends Error {
  constructor(public status: number, public code: string, public requestId?: string, public retryAfter?: number) {
    super(code); this.name = 'ApiError';
  }
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.';
  if (error.code === 'ANALYTICS_NOT_FOUND') return 'This assessment is unavailable to your account.';
  if (error.code === 'EVALUATION_LIMIT') return 'You have reached the limit of 20 saved smoke checks. Use the separate local research harness for further experiments.';
  if (error.code === 'EVALUATION_NOT_FOUND') return 'This evaluation or assessment is unavailable to your account.';
  if (error.code === 'EVALUATION_EXPORT_LIMIT') return 'This export exceeds 10,000 eligible events. Select fewer assessments.';
  const feedbackErrors: Record<string, string> = { FEEDBACK_NOT_FOUND: 'This completed attempt or owned report is unavailable.', FEEDBACK_STALE: 'New feedback or another decision changed this review. Reload before continuing.', FEEDBACK_KEY_CONFLICT: 'This retry belongs to different feedback. Refresh and try again.', FEEDBACK_CONFIRMED: 'This defect is confirmed. Correct a new version; the old version stays quarantined.', FEEDBACK_INVALID: 'Check the category, rating and review note.', FEEDBACK_FORBIDDEN: 'An active authorized account is required.' };
  if (feedbackErrors[error.code]) return feedbackErrors[error.code];
  const teacherErrors: Record<string, string> = {
    TEACHER_REVIEW_NOT_FOUND: 'This question is not available to your account.',
    TEACHER_REVIEW_FORBIDDEN: 'An active owning teacher account is required.',
    TEACHER_REVIEW_STALE: 'A newer version exists or the question was archived. Refresh and open the latest version.',
    TEACHER_REVIEW_KEY_CONFLICT: 'This retry belongs to another action. Reopen the question before trying again.',
    TEACHER_REVIEW_REJECTED: 'This version was rejected. Save a corrected version before approving.',
    TEACHER_APPROVAL_BLOCKED: 'Approval is blocked. Test content cannot be approved; AI drafts need fresh passing review and validation.',
    TEACHER_REVIEW_INVALID: 'Check the edit fields and include a review note.',
  };
  if (teacherErrors[error.code]) return teacherErrors[error.code];
  const generatorErrors: Record<string, string> = {
    GENERATOR_DISABLED: 'Draft generation is disabled in local settings.',
    GENERATOR_BUSY: 'Another local search or generation task is running. Wait and retry.',
    GENERATOR_LOW_MEMORY: 'Not enough free RAM for the local model. Test mode is available without LLM inference.',
    GENERATOR_MODEL_MISSING: 'The configured local model is not installed. No model will be downloaded automatically.',
    GENERATOR_MODEL_UNSUPPORTED: 'This model is outside the current lightweight adapter’s supported configuration.',
    GENERATOR_TOKENIZER_MISSING: 'The local tokenizer needs setup before AI drafts can run.',
    GENERATOR_OFFLINE: 'The local model service is not running. No cloud fallback is used.',
    GENERATOR_SERVICE_ERROR: 'The local model service could not complete this request.',
    GENERATOR_TIMEOUT: 'The local model exceeded its time limit. No draft was saved.',
    GENERATOR_TRUNCATED: 'The model stopped before completing a draft. No incomplete draft was saved.',
    GENERATOR_CONTEXT_MISMATCH: 'The model’s context count did not match the source budget. No draft was saved.',
    GENERATOR_CONTEXT_LIMIT: 'The selected text exceeds the supported model context budget.',
    GENERATOR_INVALID_OUTPUT: 'The model response did not meet the question format. No draft was saved.',
    GENERATOR_RESPONSE_TOO_LARGE: 'The model response exceeded the safe size limit.',
    GENERATOR_INSUFFICIENT_EVIDENCE: 'No suitable source passage was found. Use a topic appearing in your selected PDF.',
    GENERATOR_EVIDENCE_MISMATCH: 'The proposed citation did not match the source text. No draft was saved.',
    GENERATOR_KEY_CONFLICT: 'This retry belongs to different draft settings. Refresh the page before starting a new draft.',
    GENERATOR_DRAFT_NOT_FOUND: 'This private draft is not available to your account.',
  };
  if (generatorErrors[error.code]) return generatorErrors[error.code];
  if (error.code === 'VALIDATION_BUSY') return 'Another local operation is running. Wait and retry validation.';
  if (error.code === 'VALIDATION_KEY_CONFLICT') return 'This retry belongs to another draft. Reopen the draft and run validation again.';
  const verifierErrors: Record<string, string> = {
    VERIFIER_DISABLED: 'New review reports are disabled in local settings.',
    VERIFIER_TEST_DRAFT: 'Test-generated drafts can receive test reviews only. No AI review was run.',
    VERIFIER_BUSY: 'Another local indexing, generation or review task is running. Wait and retry.',
    VERIFIER_KEY_CONFLICT: 'This retry belongs to different review settings. Reopen the draft to start a new review.',
    VERIFIER_EVIDENCE_MISMATCH: 'The verifier quoted text outside the saved source excerpt. No report was saved.',
    VERIFIER_MODEL_CHANGED: 'The local model changed between review stages. No report was saved.',
    VERIFIER_UNSUPPORTED_TYPE: 'This review adapter supports conceptual questions only. Numerical and code checks are planned.',
    VERIFIER_CONTEXT_LIMIT: 'The complete question and source do not fit the supported local review context.',
  };
  if (verifierErrors[error.code]) return verifierErrors[error.code];
  if (error.code.startsWith('VERIFIER_')) {
    const message = generatorErrors[error.code.replace('VERIFIER_', 'GENERATOR_')];
    if (message) return message.replaceAll('draft', 'review report').replaceAll('question format', 'review format');
  }
  const ragErrors: Record<string, string> = {
    GENERATOR_REAL_REQUIRED: 'Real local AI is not enabled. Test drafts cannot be used as educational MCQs.',
    GENERATOR_DUPLICATE: 'The model repeated an earlier question. Your saved questions are retained; change the topic or try a new batch.',
    EMBEDDING_LOW_MEMORY: 'Not enough free RAM for local semantic search. Close other applications and retry.',
    EMBEDDING_NOT_INSTALLED: 'The local search model is not installed. Follow the RAG setup guide to prepare it once.',
    EMBEDDING_FAILED: 'The local search model could not run. Check the model files and local setup, then retry.',
    EMBEDDING_TIMEOUT: 'Local indexing or search took too long. Try a smaller document and close other heavy applications.',
    RAG_BUSY: 'Another local search or indexing task is running. Wait for it to finish, then retry.',
    RAG_NOT_INDEXED: 'Prepare each selected document for search first.',
    RAG_CHUNK_LIMIT: 'This document has no passages or exceeds the indexing limit. Try a smaller PDF.',
  };
  if (ragErrors[error.code]) return ragErrors[error.code];
  const pdfErrors: Record<string, string> = {
    PDF_REQUIRED: 'Choose a PDF document.', INVALID_PDF: 'This file could not be read as a valid PDF. Export it again and retry.',
    ENCRYPTED_PDF: 'Password-protected PDFs are not supported. Upload an unencrypted copy you are allowed to use.',
    PDF_NO_TEXT: 'No extractable text was found. Use a clearer scan or export a PDF with selectable text. Scans require installed Windows OCR.',
    PDF_OCR_UNAVAILABLE: 'This scan needs offline text recognition. Windows OCR could not run. Use a PDF with selectable text, or check that a Windows OCR language is installed.',
    PDF_OCR_PAGE_LIMIT: 'Use at most 10 scanned pages per upload. Split this scan into smaller PDFs.',
    PDF_PAGE_LIMIT: 'Use a PDF with 1–100 pages.', PDF_TEXT_LIMIT: 'This document contains too much text. Split it into smaller PDFs.',
    PDF_TOO_LARGE: 'Choose a PDF no larger than 5 MiB.', PDF_BUSY: 'Another PDF is being processed. Wait for it to finish, then retry.',
    PDF_TIMEOUT: 'PDF processing reached its time limit. Close heavy applications and retry, or split the PDF into fewer pages.', PDF_UPLOAD_TIMEOUT: 'The upload took too long. Try again with a smaller PDF.',
    MATERIAL_QUOTA: 'Your local library has reached its limit of 50 documents or 100 MiB. Contact the project administrator.',
    MATERIAL_NOT_FOUND: 'This material or page is not available to your account.', UPLOAD_STORAGE_UNAVAILABLE: 'Local file storage is unavailable. Check disk space and folder permissions.',
  };
  if (pdfErrors[error.code]) return pdfErrors[error.code];
  const attemptErrors: Record<string, string> = { ATTEMPT_NOT_FOUND: 'This attempt is unavailable to your account.', ATTEMPT_UNAVAILABLE: 'This assessment cannot start now. Check admission, remaining attempts and question eligibility with your teacher.', ATTEMPT_STALE: 'Newer progress was saved in another tab. Reload the saved attempt before continuing.', ATTEMPT_KEY_CONFLICT: 'This action conflicts with a previous request. Reload your saved attempt.', ATTEMPT_FINISHED: 'This attempt has already ended. Reload to view its status.', PRACTICE_BLOCKED: 'This private question is not eligible for scored practice. Real verification and fresh validation are required; test content remains blocked.' };
  if (attemptErrors[error.code]) return attemptErrors[error.code];
  const assessmentErrors: Record<string, string> = { ASSESSMENT_BLOCKED: 'Publication is blocked. All questions need current teacher approval and fresh passing checks. Test content cannot be published.', ASSESSMENT_STALE: 'This assessment changed or is no longer editable. Refresh it before continuing.', ASSESSMENT_KEY_CONFLICT: 'This action conflicts with an earlier request. Refresh and try again.', ASSESSMENT_QUESTION_UNAVAILABLE: 'A selected question is unavailable or has a newer version. Refresh the question list.', ASSESSMENT_NOT_FOUND: 'This assessment is unavailable to your account.', PARTICIPANT_UNAVAILABLE: 'No active student account matches that email. Ask the student to register first.', PARTICIPANT_LIMIT: 'This assessment has reached its limit of 200 participants.', ASSESSMENT_UNAVAILABLE: 'This code cannot grant access. Check the code and ask your teacher to confirm your email is allowed and the assessment is open.', CODE_RATE_LIMIT: 'Too many code checks. Wait one minute before trying again.' };
  if (assessmentErrors[error.code]) return assessmentErrors[error.code];
  if (error.code === 'STUDENT_PROFILE_UNAVAILABLE') return 'Your student profile is unavailable. Ask your project administrator to check your account.';
  if (error.code === 'DUPLICATE_COURSE') return 'You already have a course with this title. Open the existing course or choose a different title.';
  if (error.code === 'DUPLICATE_TOPIC') return 'This topic already exists in the course.';
  if (error.code === 'TOPIC_LIMIT') return 'This course has reached the limit of 100 topics.';
  if (error.code === 'COURSE_NOT_FOUND') return 'This course is no longer available to your account.';
  if (error.status === 401) return 'Your sign-in details could not be verified. Please try again.';
  if (error.status === 403) return 'This account does not have access to that workspace.';
  if (error.status === 409) return 'This email cannot be registered. Try signing in or use another email.';
  if (error.status === 429) return `Too many attempts. Please wait${error.retryAfter ? ` about ${Math.ceil(error.retryAfter / 60)} minute(s)` : ' a few minutes'} before trying again.`;
  if (error.code === 'REQUEST_TIMEOUT') return 'The request took too long to send. Please try again.';
  if (error.code === 'REQUEST_TOO_LARGE') return 'This request is too large. Reduce the amount of text and try again.';
  if (error.status === 422) return 'Check the form fields and their requirements, then try again.';
  if (error.status === 503) return 'The local service is not ready. Check that the backend and database are running, then try again.';
  if (error.code === 'TIMEOUT') return 'The local service took too long to respond. Please try again.';
  if (error.status === 0) return 'Cannot reach the local service. Start the backend and try again.';
  return 'The request could not be completed. Please try again.';
}

// Fixed same-origin paths avoid sending bearer tokens to a configured cloud URL.
export interface RequestOptions { token?: string; body?: unknown; method?: 'GET' | 'POST'; signal?: AbortSignal }
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const identityPath = /^\/(auth\/(register|register-teacher|login|me|logout|logout-all|change-password)|roles\/(student|teacher)|health\/ready)$/.test(path);
  const teacherPath = /^\/teacher\/(dashboard|courses(?:\?offset=\d+&limit=\d+|\/[a-fA-F0-9-]{36}(?:\/topics)?)?)$/.test(path);
  const studentPath = /^\/student\/(dashboard|preferences|attempts(?:\?offset=\d+&limit=\d+)?)$/.test(path);
  const materialPath = /^\/materials(?:\?(?:title=[^#\r\n]*|offset=\d+&limit=\d+)|\/[a-fA-F0-9-]{36}(?:\?page=\d+)?)?$/.test(path);
  const ragPath = /^\/rag\/(search|materials\/[a-fA-F0-9-]{36}(?:\/index)?)$/.test(path);
  const generatorPath = /^\/generator\/(status|drafts(?:\?offset=\d+&limit=\d+|\/[a-fA-F0-9-]{36})?)$/.test(path);
  const verifierPath = /^\/verifier\/(status|drafts\/[a-fA-F0-9-]{36}\/reports(?:\?offset=\d+&limit=\d+)?)$/.test(path);
  const validationPath = /^\/validation\/(math-check|drafts\/[a-fA-F0-9-]{36}\/reports(?:\?offset=\d+&limit=\d+)?)$/.test(path);
  const teacherReviewPath = /^\/teacher\/reviews(?:\?offset=\d+&limit=\d+|\/[a-fA-F0-9-]{36}(?:\/(?:edits|decisions|versions(?:\?offset=\d+&limit=\d+)?))?)?$/.test(path);
  const assessmentPath = /^\/teacher\/assessments(?:\?offset=\d+&limit=\d+|\/[a-fA-F0-9-]{36}(?:\/(?:save|publish|rotate|revoke|close|participants))?)?$/.test(path) || /^\/student\/assessments(?:\?offset=\d+&limit=\d+|\/join)?$/.test(path);
  const attemptPath = /^\/student\/(?:attempts\/[a-fA-F0-9-]{36}(?:\/(?:save|submit))?|assessments\/[a-fA-F0-9-]{36}\/attempts|practice\/start|learning)$/.test(path);
  const feedbackPath = /^\/(?:student\/feedback(?:\?offset=\d+&limit=\d+)?|student\/attempts\/[a-fA-F0-9-]{36}\/feedback|feedback\/reviews(?:\/[a-fA-F0-9-]{36}(?:\/decisions)?)?(?:\?offset=\d+&limit=\d+)?)$/.test(path);
  const analyticsPath = /^\/(?:student\/analytics|teacher\/analytics|teacher\/assessments\/[a-fA-F0-9-]{36}\/analytics)(?:\?offset=\d+&limit=\d+(?:&ranking=(?:true|false))?)?$/.test(path);
  const evaluationPath = /^\/teacher\/evaluation\/(?:runs(?:\/[a-fA-F0-9-]{36}(?:\/review-pack)?)?|adaptive-export)$/.test(path);
  if (!evaluationPath && !analyticsPath && !feedbackPath && !attemptPath && !assessmentPath && !identityPath && !teacherPath && !studentPath && !materialPath && !ragPath && !generatorPath && !verifierPath && !validationPath && !teacherReviewPath) throw new Error('Unsupported API path');
  const pdf = options.body instanceof Blob;
  if (pdf && !path.startsWith('/materials?title=')) throw new Error('Unsupported upload path');
  const controller = new AbortController();
  let timedOut = false;
  const abort = () => controller.abort();
  if (options.signal?.aborted) abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, (generatorPath || verifierPath) && options.body !== undefined ? 390_000 : ragPath && options.method === 'POST' || path === '/rag/search' ? 210_000 : pdf ? 120_000 : 15_000);
  try {
    const response = await fetch(`/api/v1${path}`, {
      method: options.method ?? (options.body === undefined ? 'GET' : 'POST'),
      headers: { ...(options.body === undefined ? {} : { 'Content-Type': pdf ? 'application/pdf' : 'application/json' }), ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}) },
      body: options.body === undefined ? undefined : pdf ? options.body as Blob : JSON.stringify(options.body),
      credentials: 'omit', cache: 'no-store', redirect: 'error', signal: controller.signal,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      const wait = Number(response.headers.get('Retry-After'));
      throw new ApiError(response.status, typeof payload?.error?.code === 'string' ? payload.error.code : 'REQUEST_FAILED', response.headers.get('X-Request-ID') ?? undefined, wait > 0 && Number.isFinite(wait) ? wait : undefined);
    }
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (options.signal?.aborted) throw new DOMException('Request cancelled', 'AbortError');
    throw new ApiError(0, timedOut ? 'TIMEOUT' : 'UNREACHABLE');
  } finally {
    clearTimeout(timer); options.signal?.removeEventListener('abort', abort);
  }
}

