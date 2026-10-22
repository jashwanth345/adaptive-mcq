# Frontend refresh and scanned-PDF repair

Completed 16 October 2026; regression runs on 15 October. This is a follow-up to the 24-phase handover. The earlier presentation and screenshots document the earlier interface.

## Delivered behavior

- Public home page, working login/signup navigation and a centered sign-in card.
- White/light-blue/lavender visual system, blue/violet actions and a compact role-aware sidebar.
- Teacher/student dashboard shortcuts, actual record counts, readable generation/review/attempt/result cards and responsive mobile layouts.
- PDF drag-and-drop, automatic title suggestion, selected-file summary, processing status and page-linked preview. PDF-only support and existing size/ownership limits remain enforced.
- Existing authentication, courses, drafts, verification, validation, review, assessment publication, reference codes, attempts, adaptation, feedback, analytics and evaluation behavior retained. Test generation remains labelled and cannot pass publication/scoring gates.

## PDF finding and fix

The reported `prompt 1 and 2 experiments.pdf` contains four scanned pages and **zero selectable text characters**. The original text-only extraction could not ingest it. The screenshot showed a timeout; a direct reproduction instead returned `PDF_NO_TEXT`, so the historical timeout's timing cause was not reproduced.

Text extraction stays isolated and bounded. On Windows, image-containing pages without selectable text are rendered at no more than 2,000 pixels on the longest edge and read by the installed Windows OCR engine. Up to 10 scanned pages are accepted. Text and OCR chunks are merged in original page order, with a distinct stored splitter version identifying OCR provenance. The preview identifies recognized pages and asks the user to inspect the source. Blank or unreadable pages remain explicitly identified.

The two worker processes are supervised directly, never inherit the application's stdin, and have separate 30-second extraction / 45-second OCR limits. Temporary images are removed after success or failure. The browser budget is 120 seconds. No database migration, LLM, cloud call, API key or paid package is needed. Windows OCR is **FREE installed Windows functionality**, not an open-source model; it is an optional platform capability. Selectable-text PDF support continues on other platforms. The engine and installed recognition languages are described in [Microsoft's OCR documentation](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine).

OCR is a source-reading aid, not factual or mathematical verification. No OCR accuracy percentage or AI-quality result is claimed. Low-quality scans, handwriting, unsupported languages, mathematical notation and complex layouts may still need manual correction or a better source.

## Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Backend regression | 318 passed; 1 real-embedding test skipped | [Log](evidence/frontend-refresh/refresh-backend-complete.log) |
| Frontend regression | 118 passed across 15 files | [Log](evidence/frontend-refresh/refresh-frontend-final.log) |
| Database SQL checks | 119 passed | [Log](evidence/frontend-refresh/refresh-database.log) |
| Migration runner | 7 passed | [Log](evidence/frontend-refresh/refresh-migrations.log) |
| Foundation browser checks | 53 passed, including the reported scanned PDF | [Log](evidence/frontend-refresh/refresh-browser.log) |
| Classroom browser checks | 14 passed | [Log](evidence/frontend-refresh/refresh-classroom.log) |
| Final help-text follow-up | 11 passed across 2 affected files; overlaps the frontend suite | [Log](evidence/frontend-refresh/refresh-copy-tests.log) |
| Final production build | Passed | [Log](evidence/frontend-refresh/refresh-build.log) |
| Backend lint | Ruff passed | Checked after implementation |

The browser checks cover both roles, authentication, upload and source preview, mock generation, verification and review gates, publication, reference codes, attempts, saved answers, submission, feedback/quarantine, analytics, responsive layouts and recovery from a stopped backend. The supplied four-page scanned PDF was successfully processed through the browser, its OCR provenance persisted, and page navigation worked. No browser runtime errors or unexpected external requests occurred in these checks.

Tests use disposable accounts/databases; the user's saved account and materials were not reset. Classroom approval evidence, scores and screenshots use synthetic fixtures, not measured AI accuracy or learner-study results. Heavy local LLM inference and embedding benchmarks are excluded under the laptop's memory constraints. The backend run reported one dependency deprecation warning. AI generation remains mock/test mode, with publication and scoring restrictions intact.

The full regression runs preceded a final help-text and spacing cleanup. The affected materials/RAG tests and production build passed again afterward; the complete suites were not repeated for that cleanup.

On 16 October the existing native database was restarted using PostgreSQL's own process checks after the wrapper encountered a stale process marker. No saved database was reset. The final website returned HTTP 200, and the API readiness check confirmed database, schema, pgvector, runtime role and authentication permissions were healthy. The local supervisor reported mock AI mode. The native wrapper's stale-marker handling remains a deployment follow-up; this frontend repair did not change that wrapper.

## Actual interface screenshots

- [Home desktop](images/frontend-refresh/home-desktop.png) and [mobile](images/frontend-refresh/home-mobile.png)
- [Login](images/frontend-refresh/login-desktop.png)
- [Teacher dashboard](images/frontend-refresh/teacher-dashboard.png) and [student dashboard](images/frontend-refresh/student-dashboard.png)
- [Reported PDF successfully processed](images/frontend-refresh/scanned-pdf-success.png)
- [Mobile assessment](images/frontend-refresh/assessment-mobile.png) and [results](images/frontend-refresh/results-desktop.png)

These are browser captures from the passing tests, before the final minor help-text/spacing cleanup. They are not generated product mockups.
