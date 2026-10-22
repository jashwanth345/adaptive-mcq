# Teacher and student user guide

Current behavior after Phases 1–22. Start with the [setup guide](setup-guide.md). Default **Test mode — no AI inference** creates software fixtures with placeholder distractors. It cannot produce publishable classroom questions or eligible adaptive practice. Approval/publication gates intentionally stay closed for those drafts. The downstream classroom workflow is implemented and was tested using isolated synthetic evidence; it is not a ready bank of validated educational questions.

## Accounts and navigation

Open `http://localhost:5173` for the home page, then choose **Login** or **Sign up**. Choose Teacher or Student in the signup Account type selector. Both roles use the same login; the stored role determines the dashboard. Accounts with both roles have both dashboards. Use **My account** for identity/password controls and **Sign out** when finished. Changing a password ends existing sessions. Refresh, page closure or token expiry requires sign-in again. There is no email password-reset workflow.

On a small screen, open **Toggle navigation**. The sidebar lists features permitted for your account. **Question bank** remains a planned dedicated screen; stored questions are accessible through Generate MCQs and Teacher review. **Recovery tools** is a planned browser screen; working operator recovery commands are documented separately.

## Teacher: organize a course

1. Open **Teacher dashboard → Create course**, enter a title and save.
2. Open the course, enter a topic and choose **Add topic**.
3. Use **Refresh overview** to reload counts. Counts describe saved records, not question quality or student achievement. A duplicate course/topic title within its owning scope is rejected.

Course rename/delete and a general enrollment-management screen are not provided. Assessment participant permissions are managed in Assessments.

## Both roles: study material and retrieval

1. Open **Study materials**, drop or choose an authorized PDF, check the suggested title and choose **Upload and process**. Default limits: 5 MiB, 100 pages; 50 stored documents or 100 MiB per owner. Text extraction also has character/time limits.
2. Open the saved document and inspect its page-linked passages against the source. On Windows, pages containing images but no selectable text use the installed offline OCR engine, with a maximum of 10 scanned pages per upload. No OCR model or paid service is downloaded. Recognized pages are labelled in the preview. Check equations, names, columns and tables carefully; OCR is not a correctness guarantee. On other systems, use selectable-text PDFs.
3. Re-uploading identical PDF bytes to the same account reuses the existing record/title. Materials stay private; a classroom membership does not grant access to the teacher's PDF library.
4. Optional semantic retrieval: **Prepare for search**, then enter a topic and **Find passages**. **View source page** links to the cited passage. This loads a local embedding model on CPU; process one small document at a time. It retrieves text, not an answer. If memory is constrained, skip this optional live step and use the recorded RAG evidence.

Extracted passages and exact quotations establish provenance, not factual correctness. A teacher must judge whether the source itself is suitable.

## Both roles: private drafts, verification and validation

1. Open **Generate MCQs**, choose a processed PDF and a topic actually present in it.
2. Choose target difficulty, cognitive level (**Remember** or **Understand**) and **10–30 questions**. In real local-AI mode, choose **Generate N MCQs** for automatic indexing and sequential generation/verification/validation. In default mock mode, only **Create test draft** works; see [AI setup and testing](question-generation.md). Targets are requests, not measured difficulty.
3. Inspect the four options, proposed key/explanation and quoted source page. In default mode, distractors are explicit placeholders; do not use these questions to assess students.
4. Reopen the item from **Saved drafts**. Private drafts persist even after signing out.
5. Use the draft's verification and validation workspaces to create advisory review/check reports. Inspect the evidence and release blockers. Mock reviews are test reports, not independent expert judgments.
6. The validation workspace also provides a bounded arithmetic preview and duplicate checks. Unsupported math cannot be certified by that validator. A passing schema or exact citation does not establish factual truth.

Generating a new question can change the duplicate comparison corpus and make older validation evidence stale. Refresh checks when prompted. Neither student feedback nor a verifier recommendation automatically starts an LLM regeneration job.

## Teacher: edit and review

Open **Teacher review**, select an owned current version and inspect the source. **Edit as a new version** saves corrected text/options/key/explanation with a reason; it preserves the old version and its audit history. The new version needs fresh checks. Mock ancestry remains mock after editing.

Use **Refresh approval checks** to see blockers. **Approve this version** requires current passing real evidence, deterministic validation, a note and explicit confirmation. In the default setup, a mock draft remains blocked. **Reject this version** records a reason; correcting a rejected/confirmed-defective version requires another version. Approval and assessment publication are separate actions.

## Teacher: assessment drafts and publication

1. Open **Assessments → Create assessment**. Choose your course, select questions and save. Pending/mock questions can be stored in an assessment draft, but cannot be published.
2. Set a time limit or leave untimed, maximum attempts, question/option randomization and result release: after submission or after closure. Each item has one point. The question set is fixed for the classroom assessment.
3. Add permitted students using their registered email addresses. This sends no message; the teacher shares the code separately. Possessing a code alone is insufficient to join.
4. When every question has current eligible evidence, use **Publish assessment**, choose expiry and confirm. This is conditional on future real eligible questions; the native browser acceptance used synthetic fixtures in isolated test databases.
5. Copy the issued code while displayed. Ordinary detail reads do not reveal it again. A replacement revokes the previous code; revocation blocks new access. Closing is permanent and revokes all codes. Published questions/settings are immutable.

Do not disable a gate, edit database evidence, or relabel mock content to make this step succeed. For a review demonstration without eligible questions, show the blocked draft and the [recorded classroom evidence](demo-script.md).

## Student: join, attempt and receive results

These steps require an eligible published assessment and explicit participant permission.

1. Sign in, open **Join assessment**, enter the teacher's current reference code and join. Code validity, permission, assessment state and attempt allowance are checked.
2. Choose **Start or resume assessment**. Joining alone does not start a timer; starting a timed attempt does. Repeated starts resume an active attempt.
3. Choose answers, navigate or mark review flags, then **Save progress**. Wait for saved confirmation before leaving. The database stores progress; unsaved selections may be lost on a crash or expiry.
4. Submit after saving and confirm. Scoring uses the server's pinned key, not a value supplied by the browser. Skips earn zero; no negative marking or partial credit is implemented.
5. Results appear according to the teacher's release policy. With after-close release, solutions and score-derived learning evidence stay hidden until closure. The timer display is advisory; the database deadline controls acceptance.

At a deadline, the next access finalizes the previously saved answers as expired and ignores late changes. There is no background finalization daemon. Already admitted attempts may finish to their original deadline after code revocation/assessment closure; new starts are blocked. Reopen saved attempts from the student workspace after signing in again. For conflicting tabs or uncertain responses, follow [troubleshooting](troubleshooting.md).

## Student: learning, analytics and feedback

- **Student dashboard:** view your activity/course memberships and save an Easy/Medium/Hard starting preference. This preference does not alter a teacher's assessment.
- **My learning:** inspect topic evidence and provisional difficulty recommendations. Insufficient data stays **Insufficient evidence**. Next practice requires a current eligible unseen question from your own private bank; default mock drafts do not qualify. An empty recommendation is expected on a new account.
- **My analytics:** view released own results and topic/difficulty/type breakdowns. No data is not zero ability. Repeated/expired attempts may appear in operational score summaries but are not independent mastery observations.
- After a submitted/expired attempt, open **Report or rate question N**, choose an issue/rating and optionally comment. Avoid personal information. **My feedback** shows your own reports/status. Reports remain possible while solutions await release, without revealing the key.

## Question owner: feedback review

Open **Feedback review** to inspect owned cases. A teacher reviews owned classroom questions; a student can review only their own private content. Mark reviewing, dismiss with a note, or explicitly confirm a defect. Counts prioritize review but do not prove an error.

Confirming a defect quarantines that exact version and prevents new use. Existing attempt snapshots and original scores remain; results label the issue under review and withhold the affected solution. Acknowledging a score-review task does **not** regrade, restore the question or notify students. Teachers create a corrected version and, after valid checks, a new assessment. Feedback does not retrain model weights.

## Teacher: analytics and evaluation

**Classroom analytics** shows owned assessment results, breakdowns, feedback and an optional ranking. Recorded score percentages describe those attempts; they are not AI accuracy. Timing includes idle time, and per-question response timing is not recorded.

In **Evaluation lab**, choose **Run synthetic smoke check**, reopen the saved check and inspect/download the evidence. The synthetic comparison exercises topic-only, context-based, verifier and math-validation stages. It is not the full adaptive-system experiment. Correctness and learning outcomes remain **To be evaluated**. Downloaded operator review packs contain a private allocation map; share only the intended reviewer items/templates. Do not publish student exports or private account data.

For backup, shutdown and recovery use the [operator guide](local-deployment.md); these are local operator actions rather than student/teacher browser features.
