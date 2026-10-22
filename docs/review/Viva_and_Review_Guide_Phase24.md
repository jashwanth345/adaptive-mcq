# Final-review speaking and viva guide — Phase 24

**ADAPTIVE MCQ GENERATION USING DUAL LLMs WITH STUDENT FEEDBACK**  
B.Tech, CSE (Artificial Intelligence and Machine Learning), Sri Venkateswara College of Engineering (Autonomous)  
Academic Year 2026–2027 • Updated 15 October 2026

Use this current guide with the Phase 24 deck. The original proposal guide is historical. The platform and engineering workflows are implemented; default generation/review are mocks. All reported classroom tests are synthetic. Real LLM quality, independent-model verification and learning outcomes remain **To be evaluated**. Durations below are rehearsal targets, not audio measurements; time your delivery and adjust pauses.

## 1-minute explanation

Our project is Adaptive MCQ Generation Using Dual LLMs with Student Feedback. We have implemented a local assessment platform for teachers and students, inspired by the 2024 IEEE Access MCQGen paper.

Teachers can organize courses, upload PDFs, review versioned questions and manage assessments. Students can join permitted tests, save answers, receive released results and report problems. Local retrieval, validation gates, a candidate adaptive policy and evaluation tools support these workflows.

The generator and verifier have separate interfaces, but this 8 GB laptop uses labelled mocks. No real LLM has been run, and mock questions cannot be published. Native database, classroom and backup-recovery tests passed using synthetic records. Our contribution is the working local integration and evidence controls; AI correctness and learning benefits still require evaluation.

## 3-minute explanation

Our project addresses the effort of producing reliable multiple-choice questions and the need to respond to different student learning levels. A fluent question may still have an incorrect key, weak distractors or unsupported information. We therefore treat generation as the beginning of a controlled workflow.

The research foundation is the 2024 IEEE Access MCQGen paper by Ching Nam Hang, Chee Wei Tan and Pei-Duo Yu. It combines GPT-4, retrieval, chain-of-thought prompting and self-refinement. It already includes teacher involvement, feedback and adaptive difficulty. Its quality evaluation covers 60 questions, while its learning example follows two students. The authors identify limited evaluation breadth and domain, language and model-comparison limitations. We do not describe that paper as unevaluated or entirely static.

Our implemented application uses React, FastAPI and native PostgreSQL with pgvector. PyMuPDF extracts private study material with page provenance, and Sentence Transformers supports local semantic retrieval. Questions retain their source links and versions. Separate generator and verifier interfaces support a blind-answer stage followed by critique. Structural, source, duplicate and bounded arithmetic checks contribute to release eligibility.

Teachers can edit a new question version, review evidence and manage assessment drafts. Publication requires fresh passing real evidence and teacher approval. Students need an active reference code and explicit participant permission. The server saves answer state, grades pinned question versions and enforces the result-release policy. Feedback can lead an owner to confirm a defect and quarantine future use without silently changing historical scores.

My learning derives topic evidence and uses a candidate difficulty policy for private practice. Fixed classroom question sets do not adapt. The thresholds are assumptions that need calibration; an insufficient-evidence state is not a student failure.

The important limitation is hardware and AI validation. This laptop has 8 GB RAM and no dedicated GPU. We use clearly labelled mocks; no LLM was downloaded or run. Ordinary mock drafts cannot become classroom questions. Positive classroom tests use isolated synthetic evidence. Phase 22 passed 58 targeted regressions, 14 native classroom browser checks, and a separate backup/restore rehearsal with matching records and PDF hashes. Those are engineering results, not AI accuracy. Real model trials, independent human ratings and learner studies remain future work.

## 5-minute explanation

Good morning. Our project is Adaptive MCQ Generation Using Dual LLMs with Student Feedback. We have built a local teacher and student assessment platform and completed its engineering documentation and final-review evidence package. The core has no paid API, subscription or mandatory cloud service.

The problem has two parts. First, creating a good MCQ requires a clear stem, one defensible answer, plausible distractors, a useful explanation and suitable source material. Automatic generation can produce convincing errors, especially in mathematics. Second, students have different learning needs, so practice should respond to reliable evidence of their performance. A question-quality problem must not be mistaken for a learner's lack of understanding.

Our research foundation is the 2024 IEEE Access MCQGen paper by Hang, Tan and Yu. It uses GPT-4 with retrieval and prompting techniques including chain-of-thought and self-refine. Its knowledge base combines instructor and student-created questions. The paper already includes teacher involvement, student feedback and difficulty adaptation. We therefore do not claim those ideas as our inventions. Its evaluation includes 60 questions across mathematics, concepts and coding, with three lecturer evaluators and three other LLM evaluators. Its learning example follows two students over 12 lectures. The authors acknowledge limits in quantitative breadth, sample size, Computer Science and English scope, and generation-model comparison.

Our system turns the proposed extension into an auditable application workflow. React, Vite and Tailwind provide the frontend. FastAPI owns authentication, permissions, scoring and feature APIs. Native PostgreSQL stores users, materials, question versions, assessments, attempts and evidence; pgvector supports local semantic retrieval. PyMuPDF preserves extracted page references, and a local Sentence Transformer creates embeddings. Uploaded files stay on the computer. RAG supplies relevant evidence, but similarity or an exact quotation does not prove that the source or answer is correct.

The AI design has separately configurable generator and verifier roles. The generator contract returns a question, options, key, explanation and metadata. The verifier first solves without seeing the key, then critiques the candidate. This reduces direct answer anchoring, but separate prompts do not guarantee independent errors. Additional gates check structure, source provenance, duplicate evidence and supported exact arithmetic. Unsupported mathematics is not silently certified. A teacher edit creates a new immutable version that needs fresh checks.

Teachers organize courses, manage question review and create classroom assessment drafts. Publication requires eligible current evidence and explicit teacher approval. Students join using both a valid reference code and participant permission. Their attempt pins the question and option order. Saving commits progress, submission grades on the server, and results obey after-submit or after-close release. Codes, deadlines and maximum attempts are enforced by the backend. Fixed classroom assessments remain fixed.

Student reports refer to exact versions. An owner can review and confirm a defect, which quarantines future use and opens score review. Original answers and scores remain preserved; acknowledgement does not regrade. The learning policy excludes defective evidence and uses eligible released first exposures. Its difficulty estimates have explicit coverage and promotion/demotion rules, but they are a candidate policy rather than a calibrated measure of ability.

Our current evidence is engineering evidence. Native setup and startup passed; the Phase 22 regression had 58 passes and its native classroom journey had 14 browser passes. A separate native backup/restore matched application records and three PDF hashes, revoked previous sessions and allowed fresh sign-in. All classroom fixtures were synthetic. These counts must not become an accuracy percentage or a student-study sample.

Finally, this 8 GB laptop runs mock generation and review. No real generator/verifier LLM was downloaded or executed. Mock drafts remain blocked from publication, while the implemented positive classroom path was tested separately with synthetic evidence. The evaluation harness prepares matched comparisons and human-review packs, but real AI correctness and learning benefits remain to be evaluated. Our contribution is the local integration, explicit quality gates and reproducible evidence framework. Hardware-approved model trials, independent ratings and controlled learner studies are the next research steps.

## Expected faculty questions

### 1. What have you actually completed?

The local web application, account/role controls, teacher/student workspaces, PDF pipeline, local retrieval, mock-tested AI adapters, versioned review and release gates, classroom attempts, candidate adaptation, feedback/quarantine, analytics, evaluation tooling, native deployment/recovery and documentation. Real LLM performance and learner benefits remain unvalidated. See the [current limitations](adaptive-mcq/docs/limitations.md).

### 2. Is the project fully complete?

The 24-stage engineering roadmap is complete with its stated deferrals. That is not a claim that every original research ambition is finished. Real AI inference, broad question formats, OCR, additional languages, learner studies and dedicated Question bank/Recovery tools screens remain open.

### 3. What is your accuracy?

We have no valid project AI-accuracy figure. Test passes measure expected software behavior on specified fixtures. We need real held-out questions, independent ratings, explicit denominators and uncertainty before reporting factual correctness or answerability.

### 4. Why does the title say dual LLMs if the demo uses mocks?

It names the intended AI architecture. The separate adapter contracts and review workflow are implemented, while the laptop demonstration uses mocks under the hardware constraint. We disclose that boundary on the cover and technical slides. We do not claim a real dual-model experiment.

### 5. Can the website run on this laptop?

The prepared local website and native workflow tests ran with lightweight fixtures. That does not establish that real model inference or maximum-size retrieval fits safely at all times. RAM, CPU contention and free storage vary; the normal launcher keeps mock mode and does not start Ollama.

### 6. Is the project really free?

The core runs locally without paid APIs, hosting, database services, credit cards or subscriptions. The ₹0 target is service/subscription cost, excluding existing hardware, electricity and internet. The C++ build tools used for pgvector are free proprietary tools, not open-source runtime components.

### 7. How do you demonstrate publication if mocks cannot publish?

Show the live draft and the correctly blocked gate, then the clearly labelled screenshots and recorded native synthetic classroom acceptance. Never modify evidence or switch off checks to make the demo look complete. The positive integration fixture is not a real AI-generated classroom bank.

### 8. How is this different from asking a chatbot?

The platform adds private source provenance, immutable versions, permissions, approval/release rules, reference-code admission, saved attempts, server grading, quarantine, analytics and recovery. These mechanisms are testable independently of the quality of a particular model.

## Technical viva questions

### 9. Generation, verification and validation: what is the difference?

Generation proposes content. Verification gives an advisory judgment about that content. Validation checks explicit contracts such as schema, source integrity, duplicate evidence or supported arithmetic. Release combines these with current eligibility and teacher control; none alone proves universal correctness.

### 10. Is generation a durable background job?

No. Successful drafts and provenance persist, but there is no durable cross-restart in-progress queue. The bounded backend operation may finish after browser navigation; saved history reveals committed results. Do not present the original planned queue as implemented.

### 11. What happens to malformed model output?

Strict structured parsing and schema checks reject invalid candidates. Source and other checks can reject structurally valid but unsupported output. A failure is not stored as a successful educational result or silently replaced with a paid cloud call.

### 12. Why not execute code written by the model to check mathematics?

Untrusted generated code could access files or perform arbitrary operations. The validator uses a bounded supported arithmetic contract and independent exact calculation. It does not execute model-written Python or certify general mathematical proofs.

### 13. How do you handle duplicates?

Deterministic duplicate checks produce versioned reports tied to a comparison corpus. If that corpus changes, evidence can become stale and need rechecking. This is not a guarantee that every semantic paraphrase in every language is detected.

### 14. What is quantization?

It represents model parameters at reduced precision to reduce storage and usually memory demand, with possible quality tradeoffs. File size is not total inference RAM: context, caches, runtime and the rest of the application also consume memory. No quantized LLM has been validated here.

### 15. Is difficulty the same as cognitive level?

No. Difficulty concerns how challenging an item is for a population; cognitive level describes the kind of thinking requested. Current generation controls are narrow, including Remember/Understand. Requested labels are not empirically calibrated item difficulty.

### 16. What happens with scans and complex equations?

OCR is not included. PDFs need extractable text, and tables/equations may extract imperfectly. Review the page evidence and reject unsuitable material; do not invent missing text or claim that source extraction guarantees mathematical fidelity.

## Questions about the 2024 paper

### 17. What is the exact reference?

Ching Nam Hang, Chee Wei Tan and Pei-Duo Yu, “MCQGen: A Large Language Model-Driven MCQ Generator for Personalized Learning,” IEEE Access, volume 12, pages 102261–102273, 2024. DOI: [10.1109/ACCESS.2024.3420709](https://doi.org/10.1109/ACCESS.2024.3420709). The supplied paper is the primary source.

### 18. What is its main method?

GPT-4 generation combined with retrieval from a knowledge base, chain-of-thought prompting and self-refine. It uses instructor/student-created questions and feedback/performance to support educational relevance and adaptation. See its Section III and adaptation discussion in Section V.

### 19. What evaluation did it report?

60 generated questions: 20 mathematics, 20 concept and 20 coding items in Computer Science. Three lecturers and GPT-3.5, LLaMA-2 and PaLM 2 evaluated quality. The learning example covers two students over 12 lectures. Those numbers belong to the paper, not our project.

### 20. Did it use only one LLM?

It used GPT-4 as its generator but other LLMs as evaluators. “One generator without a broad generation-model comparison” is the accurate limitation. Saying that it never used multiple LLMs in any role would be false.

### 21. Did it already use adaptation and feedback?

Yes. We extend the operational design with explicit evidence, versioning, feedback review/quarantine and a candidate topic policy. We do not claim to invent feedback, teacher involvement or adaptive assessment.

### 22. What mathematical issue motivates stronger checking?

The paper discusses cases where the mathematically correct answer is absent from the offered options. A deterministic calculation for supported item types can test whether exactly one option matches. Our limited validator is not a solution to all mathematical reasoning.

### 23. Was its evaluation entirely qualitative or absent?

It includes scored human/model evaluations and reports figures. Section VII acknowledges insufficient extensive numerical evaluation and small samples. The defensible criticism is limited breadth and generalizability, not “no evaluation.”

## Questions about project improvements

### 24. Which additions matter most?

Explicit provenance and immutable versions, separate review contracts, supported deterministic checks, teacher-controlled release, saved attempts, feedback quarantine and a testable evaluation/recovery workflow. The value of real AI filtering still needs measurement.

### 25. Are these additions guaranteed to improve quality?

No. They may reject good items, retain bad ones or increase latency. An experiment must measure false acceptance, false rejection, retention and human quality under matched conditions. More components alone do not prove improvement.

### 26. Why does editing invalidate earlier approval?

The earlier evidence refers to specific text, options and version. An edit can change the correct answer or source support. A new immutable version preserves history and requires fresh evidence, preventing silent changes to an assessment already attempted.

### 27. What is the “2025 system” mentioned in the original abstract?

No supporting 2025 paper was supplied for that claim. We should not cite it as established evidence or claim priority over it. The final deck grounds research claims in the supplied 2024 paper and verified project artifacts.

### 28. How do you improve diversity?

The architecture and contracts support requested attributes, and the evaluation plan includes diversity and complexity. Current generation is narrow; broad item types and measured diversity improvement are deferred. Duplicate detection alone is not a diversity metric.

## Questions about dual LLMs

### 29. Why have a separate verifier role?

It makes review a separate contract with its own inputs and evidence. A blind-answer stage can challenge a proposed key before critique. Its benefit must be validated; it is not an infallible judge.

### 30. How do you reduce agreement bias?

The first solving stage withholds the generator's key and explanation. A later stage compares them. Models can still share training biases or reasoning failures, so human and deterministic checks remain necessary.

### 31. Can both roles use the same checkpoint?

The current supported candidate does, with separate settings/roles. That is a two-role workflow, not independent-model evidence. A genuinely different checkpoint needs supported tokenizer/template behavior, hardware testing and quality evaluation.

### 32. Where are the originally requested Gemini models?

They are not used. The project has no Gemini API dependency or local Gemini weights. The later local-only requirement superseded the early diagrams. We must not rename a local model “Gemini” or silently call a cloud service.

### 33. What is the current model selection?

**Hardware-validated model selection: pending.** The guarded adapter candidate is `qwen2.5:0.5b-instruct-q4_K_M` for both roles. It is not downloaded or quality-approved. Larger early candidates are no longer the active recommendation. The application remains mock unless a separate authorized hardware trial succeeds.

### 34. What happens if the verifier disagrees?

Its report is advisory and may recommend pass, regenerate or reject. Release still needs all other checks. There is no automatic unlimited regeneration loop, no fallback to a paid API and no permission to publish a mock pass.

## Questions about RAG

### 35. What is RAG?

Retrieval-augmented generation supplies relevant external source passages to a generator. Here the retrieval stack is local: PDF extraction, chunks, Sentence Transformers and pgvector. Current mock drafting is a separate keyword fixture path and must not be described as real semantic RAG generation.

### 36. Is RAG fine-tuning?

No. It changes the context supplied at inference; it does not update model weights. This project does not fine-tune or retrain a model from student feedback.

### 37. Why embeddings and pgvector?

Embeddings represent text for similarity retrieval. The pinned MiniLM pipeline produces 384-dimensional vectors, and pgvector stores/searches them beside relational provenance locally. Similarity is a retrieval signal, not a truth probability.

### 38. How are chunks sized?

Ingestion uses page-bounded character chunks with overlap. Embedding uses actual tokenizer windows and pooling so the text is covered. A generator uses its own tokenizer and reserves output space. The ingestion byte-count estimate is not a generator-token measurement.

### 39. Does grounding eliminate hallucination?

No. A source may be wrong, retrieval may select irrelevant content, or a model may infer unsupported conclusions. Exact quotes and citations aid auditing; they do not establish every claim or answer.

### 40. Can students generate from a bare topic?

The present private draft flow requires owned processed material and a topic found in it. Unrestricted topic-only source generation is not implemented in that product flow. The evaluation harness's synthetic topic-baseline condition is a separate experiment tool.

## Questions about adaptive learning

### 41. What is the implemented algorithm?

`bounded-performance-v1` derives topic/difficulty evidence with a symmetric prior, decay and minimum coverage. A difficulty estimate is `(1 + decayed correct)/(2 + decayed responses)`. Recommendations change by at most one level under the documented recent-response thresholds. It is an explicit candidate policy, not a trained or calibrated learner model.

### 42. Which answers count?

Eligible first-exposure evidence from submitted, released, approved items. Skips, expired attempts, repeated exposure and quarantined items are excluded. This avoids treating repeated attempts or defective questions as independent ability observations.

### 43. Why not always make the next question harder after one correct answer?

One response is weak evidence and may be a guess. The candidate policy requires coverage and recent-response conditions. The selected thresholds are design assumptions that need evaluation, not established optimal values.

### 44. Do timed classroom tests adapt per student?

No. Published classroom versions and item sets are fixed. Adaptation recommends eligible private practice after released evidence. This avoids silently changing a graded classroom assessment's comparability.

### 45. Does speed or a complaint lower mastery?

No. Per-question response time is not currently measured, and comments do not directly penalize ability. Confirmed defective versions are excluded from evidence through quarantine. Elapsed attempt time in analytics includes idle time.

## Questions about database and backend

### 46. Why keep immutable question versions?

They preserve the exact content answered and reviewed. Attempts pin version and option-order snapshots. Later corrections create a new version, so historical scoring and feedback do not silently point to changed text.

### 47. Who calculates scores?

The backend maps submitted displayed choices through the saved option permutation and compares the immutable key. Clients cannot supply awarded points or correctness. Current items have one point; skips earn zero and there is no negative marking/partial credit.

### 48. Is a reference code enough to join?

No. The signed-in student must be explicitly permitted, and the backend also checks code state/expiry, assessment eligibility and allowance. Codes are access conveniences, not substitutes for authentication and authorization.

### 49. How are roles and passwords protected?

Public registration grants only student access. Teacher enrollment uses the trusted operator flow. Passwords use Argon2; short-lived JWTs are tied to revocable database sessions. Browser tokens remain in memory. Every request checks identity/roles and ownership; the API uses a restricted database login.

### 50. What survives a restart?

Saved database records and PDFs persist. Phase 22 exercised a clean API restart, retry behavior, an immediate database restart and a separate database/PDF restore. Unsaved browser input is not guaranteed, and a database restart test is not a whole-machine power-loss durability certification.

### 51. How does restore protect live data?

It uses a new empty target database and separate staged PDF folder, verifies files and readiness, reapplies grants and revokes restored sessions. It does not automatically overwrite `.env`, merge uploads or cut over live data. Backups contain private records and password hashes and must be protected.

## Questions about novelty

### 52. What is your research novelty claim?

We claim an implemented engineering integration and explicit evidence controls under a local hardware/cost constraint. RAG, verification, teacher review and adaptive practice are established ideas. A stronger research novelty claim needs broader literature comparison and actual results.

### 53. Are reference codes an AI innovation?

No. They are a classroom usability/access feature. Their value is in a coherent assessment workflow with authorization and auditable state, not a new AI algorithm.

### 54. Is this better than MCQGen?

That is not yet demonstrated. The deployment and workflow choices differ, but engineering acceptance does not establish better question quality or learning gains. We need a fair controlled comparison before making that claim.

## Questions about evaluation

### 55. What do A/B/C/D compare?

A generates from topic only; B uses frozen local retrieved context; C verifies the same B candidate; D adds bounded math checks to it. This is a matched filtering ablation with failures retained. It is not yet a complete adaptive-learning outcome trial.

### 56. What should you measure?

Factual correctness, answerability, source support/relevance, distractor quality, requested-versus-rated difficulty, diversity/complexity, duplication, latency and retained/rejected yield. Learner satisfaction and learning gains require a separate participant study. Define denominators and missing-data handling before collecting results.

### 57. Why independent human reviewers?

The verifier's own judgment cannot be its ground-truth label. The harness prepares blinded candidate packs and an anchored rubric for independent ratings, disagreement and adjudication. Such completed real-item ratings are not available yet.

### 58. Do 58 passing tests mean 100% accuracy?

No. The 58 are selected Phase 22 software checks, not a representative MCQ dataset. The 14 native browser checks are workflow scenarios. The eight acceptance groups include that browser journey and must not be summed as independent observations.

### 59. What evidence is available now?

Recorded functional and security suites, actual UI captures using synthetic fixtures, native startup/authentication/permissions, bounded transaction contention and separate backup/restore matching records and PDF hashes. See the [evidence register](Final_Review_Evidence_Register.md). No real model or learner results are available.

### 60. What must happen before reporting learning improvement?

Define an appropriate fixed-versus-adaptive comparison, suitable participants/materials, consent/privacy arrangements, outcome measures, baseline, sample-size rationale and analysis plan. Calibrate the policy and evaluate real educational questions. Do not transform operational score histories or synthetic test fixtures into a causal learning claim.

## Review preparation

Use the [demonstration script](adaptive-mcq/docs/demo-script.md), [setup guide](adaptive-mcq/docs/setup-guide.md) and [limitations](adaptive-mcq/docs/limitations.md). Rehearse the mock-publication explanation before review. Preserve the boundary between paper evidence, source design, implementation tests and future research in every answer.
