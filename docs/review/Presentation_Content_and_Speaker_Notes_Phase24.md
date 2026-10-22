# Final-review presentation content and speaker notes — Phase 24

ADAPTIVE MCQ GENERATION USING DUAL LLMs WITH STUDENT FEEDBACK

22 slides • Academic Year 2026–2027 • Updated 15 October 2026

The implemented local platform is distinguished from synthetic engineering tests and future research. Default AI is mock; real model quality and learning benefit remain **To be evaluated**. Every slide below includes its visible content and the speaker notes embedded in the PPTX. Use the [evidence register](Final_Review_Evidence_Register.md) and [speaking/viva guide](Viva_and_Review_Guide_Phase24.md).

## Slide 1 — ADAPTIVE MCQ GENERATION USING DUAL LLMs WITH STUDENT FEEDBACK

**Status:** FINAL REVIEW • LOCAL SOFTWARE IMPLEMENTED • AI DEMO USES MOCKS

**On-slide content**

- Sri Venkateswara College of Engineering (Autonomous)
- B.Tech  /  Computer Science and Engineering (Artificial Intelligence and Machine Learning)
- ADAPTIVE MCQ GENERATION / USING DUAL LLMs / WITH STUDENT FEEDBACK
- AI-Powered Adaptive Assessment Using RAG and Dual-LLM Verification
- Study / material
- Generator + Verifier / Mock demonstration
- Adaptive practice
- PROJECT TEAM 11
- 23BFA33318    V. NaveenKumar / 23BFA33310    V. Jashwanth / 23BFA33328    G. Sai Koushik / 23BFA33295    P. Theja Bhuvan Reddy
- GUIDE
- Dr. D. Kavitha / Associate Professor / Dept. of CSE (AI & ML)
- Academic Year 2026–2027

**Speaker notes**

Good morning. Our project is Adaptive MCQ Generation Using Dual LLMs with Student Feedback. We have implemented a local teacher/student assessment platform and its evidence-controlled workflows. This final review separates existing MCQGen research, implemented engineering, synthetic tests and future AI evaluation. On the supplied 8 GB Windows laptop, generation and advisory review remain in explicitly labelled mock mode. No generator/verifier LLM was downloaded or run, and we do not claim AI accuracy or learning improvement. The title states the intended AI architecture, not a completed independent-model experiment. Team names and roll numbers, guide, institution and academic year follow the supplied project abstract. Sources: supplied abstract; docs/phase-22-completion.md; docs/phase-23-completion.md.

## Slide 2 — Problem statement

**Status:** MOTIVATION

**On-slide content**

- Question quality and learner differences require more than automatic generation
- Traditional / assessment
- Static / questions
- Limited / personalization
- Learning / gaps
- Authoring effort
- Manual creation and / balanced difficulty take time.
- Unreliable questions
- Hallucinations, weak distractors / and wrong math answers.
- Unequal learning needs
- Fixed tests and unused / feedback miss individual gaps.
- Design challenge: reliable questions and appropriate next practice

**Speaker notes**

Manual MCQ construction requires subject expertise and time. AI generation can help draft questions, but relevance, plausible distractors, answer correctness and mathematical answerability still require checking. A fluent question may be wrong. Fixed assessments can also miss differences between learners. Our problem combines reliable question construction with appropriate subsequent practice. The traditional-assessment diagram is a simplified problem framing, not a claim that every conventional assessment lacks personalization. The paper itself already addresses adaptation, so this slide must not be used to describe MCQGen as entirely static. Sources: MCQGen, Sections I, IV-B and VI, printed pages 102261â€“102262 and 102269â€“102271; supplied requirements.

## Slide 3 — Existing system: 2024 MCQGen

**Status:** EXISTING RESEARCH

**On-slide content**

- GPT-4 generation with RAG, CoT and self-refine prompting
- Hang, Tan & Yu  •  IEEE Access, 2024
- Instructor-designed + / student-created MCQs
- RAG / Knowledge retrieval
- GPT-4 / MCQ generation
- CoT + self-refine / Prompt engineering
- Student performance / + instructor feedback
- Adaptive / difficulty
- Research foundation for our project
- DOI: 10.1109/ACCESS.2024.3420709   ·   Method: Section III   ·   Adaptation: Section V

**Speaker notes**

Hang, Tan and Yu published MCQGen in IEEE Access, volume 12, pages 102261â€“102273, 2024, DOI 10.1109/ACCESS.2024.3420709. Its RAG knowledge base combines instructor-designed and student-created MCQs. The paper reports 605 knowledge-base questions: 530 instructor-created and 75 student-created. Self-refine improves the stem and key; chain-of-thought prompting supports distractor construction and review. Instructors use performance and feedback to adjust subsequent questions. Human involvement and student feedback are therefore existing features. Our project extends this foundation with an explicit local generator/verifier pipeline and operational controls. Source: paper Sections III-Aâ€“C and V, printed pages 102263â€“102270, Figures 1 and 3. This is a conceptual redraw, not a reproduction of implementation code.

## Slide 4 — Limitations supported by the paper

**Status:** EXISTING RESEARCH

**On-slide content**

- Small studies and quality challenges limit the strength of the evidence
- 60 MCQs
- 3 lecturers + 3 model evaluators
- 2 students
- Learning example over 12 lectures
- 1 generator
- GPT-4, no generator comparison
- Evidence scope
- Limited quantitative breadth; small samples
- Coverage
- Computer Science evaluation; English-only generation
- Question quality
- Diversity, complexity and math answerability challenges
- Further development
- Stronger checks and richer personalization warrant study
- Sections IV–VII. The paper already includes instructor verification, adaptation and feedback.

**Speaker notes**

The paper does contain evaluation. It tests 60 generated MCQs, with 20 each for mathematics, concepts and coding, using three computer-science lecturers plus GPT-3.5, LLaMA-2 and PaLM 2 as machine evaluators. Its educational example describes two students across 12 lectures. Section VII explicitly identifies the absence of extensive numerical evaluation, small samples, a computer-science-only evaluation, GPT-4-only generation without generator-model comparison, and English-only generation. Sections IV-B and VI discuss weaker diversity, complexity and math answerability. The paper reports cases where the exact mathematical answer is absent from the options. Stronger automated verification and richer mastery tracking are our responses to these observations, not claims that the original authors did no verification or adaptation. Sources: Sections IVâ€“VII, printed pages 102268â€“102272.

## Slide 5 — Research gap and project response

**Status:** IMPLEMENTED MECHANISMS / PLANNED RESEARCH

**On-slide content**

- Implemented controls and research hypotheses have different evidence requirements

| 2024 approach | Extension in this project | Current evidence |
| --- | --- | --- |
| GPT-4 + self-refine | Generator / reviewer roles | Mock-tested; inference pending |
| Math answerability issues | Bounded exact-arithmetic gate | Implemented; limited math scope |
| Diversity / complexity limits | Difficulty + cognitive controls | Narrow concepts; breadth deferred |
| Small evaluation studies | Matched evaluation harness | Synthetic; real study planned |
| Response-based adaptation | Evidence-based topic profile | Candidate rules; not calibrated |
| English-focused study | Additional languages / domains | Future work |

- These are engineering responses; superiority over MCQGen has not been demonstrated.

**Speaker notes**

The 2024 paper already uses teacher involvement, refinement, adaptation and student feedback. Its separate LLM evaluators are not the same as a production generator/verifier release workflow. Our project implements explicit generation/review contracts, bounded validation, immutable versions and operational controls. These additions are engineering responses to the paper’s limitations, not proof of improved question quality. Only a narrow conceptual generation contract and Remember/Understand controls are available; broad diversity and multilingual support remain future work. The adaptive policy exists but is uncalibrated. Controlled real model and human evaluations remain necessary. Sources: MCQGen Sections III–VII, DOI 10.1109/ACCESS.2024.3420709; docs/limitations.md, validation.md, attempts-and-adaptive.md, evaluation.md.

## Slide 6 — Implemented platform and AI boundary

**Status:** IMPLEMENTED PLATFORM • MOCK AI DEFAULT

**On-slide content**

- The local website works; real generator/verifier inference remains unvalidated
- A local assessment platform with explicit evidence and release gates
- Teacher + Student
- React web application
- FastAPI backend
- Local RAG + AI adapters
- Validation + teacher review
- Eligible versioned questions
- Fixed tests + private practice
- Performance + feedback
- Adaptive engine + analytics

**Speaker notes**

React communicates with FastAPI; PostgreSQL/pgvector and local PDF storage retain private records and provenance. Teachers organize courses, review versions, manage assessment drafts, participant permissions and classroom analytics. Students have private materials/drafts, admission and attempt workflows, feedback and learning views. Release requires eligible evidence. Normal mock drafts cannot be approved, published or selected for private practice; positive classroom workflows were exercised using isolated synthetic fixtures, not real AI output. The overview is an architecture, not a claim that every arrow runs automatically on every answer. There is no durable background generation queue or automatic feedback-driven model training. Sources: docs/user-guide.md, generator.md, teacher-review.md, phase-22-completion.md.

## Slide 7 — Objectives and delivery status

**Status:** ENGINEERING IMPLEMENTED • BENEFITS TO BE EVALUATED

**On-slide content**

- Software mechanisms are implemented; educational outcomes remain hypotheses
- 01
- Context-aware generation
- PDF provenance + local retrieval implemented.
- 02
- Separate review role
- Review contracts built; real quality untested.
- 03
- Numerical reliability
- Bounded exact arithmetic implemented.
- 04
- Teacher control
- Versioned review + publication gates built.
- 05
- Personalized practice
- Candidate policy; learner benefit untested.
- 06
- Measurable quality
- Harness built; AI experiments still planned.

**Speaker notes**

We distinguish mechanism from outcome for each objective. Source ingestion and local retrieval are implemented; generation quality is not measured. A separate review role exists, but independent-model correctness is unvalidated. Supported arithmetic can be checked deterministically, while unsupported mathematics cannot be certified. Versioned teacher decisions and classroom controls are implemented. Private adaptation uses a candidate policy that needs calibration. Evaluation tooling exists to collect future evidence, but does not itself supply real AI or student results. Sources: docs/limitations.md and the relevant implementation guides.

## Slide 8 — Users and actual frontend

**Status:** ACTUAL UI • SYNTHETIC PHASE 20 TEST DATA

**On-slide content**

- Role-specific dashboards from the implemented application
- TEACHER
- STUDENT
- Actual dashboard screenshot, cropped for readability; synthetic Phase 20 test data.
- Actual dashboard screenshot, cropped for readability; synthetic Phase 20 test data.
- Courses • PDFs • review • assessments / Participant access • classroom analytics
- Private PDFs / drafts • join • save / submit / Released results • feedback • learning
- Actual frontend screenshots • synthetic test records • no measured learner outcomes

**Speaker notes**

These are actual frontend captures from Phase 20 browser tests, replacing the original concept wireframes. Their users, records and counters are synthetic fixtures; no numbers are learner-study findings. The teacher workspace supports courses/topics and navigation to materials, drafts, review, assessments and analytics. The student workspace supports own activity/preferences and navigation to materials, joining, attempts, feedback and learning. Backend identity and ownership checks enforce access; hiding navigation alone is insufficient. A dedicated Question bank screen and browser Recovery tools screen remain Planned, although questions persist and operator recovery commands work. Sources: docs/images/phase-20-teacher-dashboard-desktop.png, phase-20-student-dashboard-desktop.png; frontend/src/App.tsx; docs/user-guide.md.

## Slide 9 — Teacher workflow

**Status:** IMPLEMENTED WORKFLOW • MOCK PUBLICATION BLOCKED

**On-slide content**

- Versioned review and publication checks protect classroom assessments
- Login
- Create assessment
- Upload PDF + choose topic
- Create private draft
- Advisory review
- Quality validation
- Teacher review / Edit / reject / approve
- Publish approved set
- Create code + share
- Edits require fresh checks. Mock drafts remain blocked from publication.

**Speaker notes**

Teachers create courses and assessment drafts, upload authorized PDFs and choose a topic, target difficulty and cognitive level. Current default drafting produces a labelled fixture. Advisory review and deterministic validation save reports. Teachers may edit a new version or reject it; edits invalidate earlier eligibility and require fresh checks. Approval needs current passing real evidence, and publication separately rechecks all selected versions and participant settings. Mock origin persists through edits and remains blocked. Published assessment versions/settings are fixed. A reference code is displayed when issued and must be shared by the teacher. Automatic LLM regeneration is not started by feedback. Sources: docs/generator.md, teacher-review.md, assessments.md; native acceptance evidence.

## Slide 10 — Student workflow

**Status:** IMPLEMENTED WORKFLOW • SYNTHETIC CLASSROOM ACCEPTANCE

**On-slide content**

- Fixed classroom tests and eligible private practice are separate paths
- A  JOIN TEACHER ASSESSMENT
- Code + validation
- Access + attempt
- Submit + score
- Released feedback
- Released eligible answers inform provisional private-practice recommendations
- B  STUDENT SELF-GENERATION
- Own PDF + topic
- Draft + review roles
- Eligible real evidence
- Practice + analysis
- Classroom questions stay fixed. Mock drafts cannot enter eligible practice.

**Speaker notes**

A student must be registered, permitted by the teacher and holding a valid code. Starting an admitted assessment stores immutable version and option-order snapshots; joining alone does not start the timer. Save progress commits choices, and submission grades on the server. Results follow after-submit or after-close policy. Existing admitted attempts can finish to their original deadline after closure or code revocation; new starts are blocked. Eligible released first-exposure responses contribute to the candidate learning policy. Private practice requires a current eligible real-evidence question from the student’s own bank. Default mock drafts cannot enter that bank. Sources: docs/assessments.md, attempts-and-adaptive.md, user-guide.md.

## Slide 11 — Complete local system architecture

**Status:** IMPLEMENTED LOCAL STACK • INFERENCE DEFERRED

**On-slide content**

- Native data, local services and explicit separation of AI roles
- 1  FRONTEND / React + Vite + Tailwind
- 2  BACKEND / FastAPI + auth + workflows
- 5  ADAPTIVE ENGINE / Profiles + next practice
- 3  RAG PIPELINE / PDF + local embeddings / Authorized retrieval
- 4  AI / LLM LAYER / Generator + verifier adapters / Mock mode; no LLM loaded
- 7  VALIDATION / Pydantic + exact arithmetic / Source + duplicate checks
- 6  DATA LAYER / PostgreSQL + pgvector + local uploads
- 8  DEPLOYMENT / Native Windows + recovery

**Speaker notes**

The eight layers adapt the original supplied diagram to the later free/local requirement. Frontend: React/Vite/Tailwind. Backend: FastAPI, authentication and workflows. Retrieval: PyMuPDF, local Sentence Transformers and pgvector. AI: separately configured generator/verifier adapters, currently mock. Validation uses Pydantic, source/duplicate gates and bounded exact Python arithmetic; installed SymPy is not a general active proof engine. The adaptive service derives profiles from eligible answer evidence. Local files store PDFs. The dedicated PostgreSQL cluster and startup/backup/recovery tools passed native tests. No paid API, cloud database or mandatory hosted deployment is used; no durable generation-job queue is claimed. Sources: docs/local-deployment.md, limitations.md, generator.md.

## Slide 12 — Local RAG pipeline

**Status:** REAL RETRIEVAL TESTED IN PHASE 9 • MOCK DRAFTING IS SEPARATE

**On-slide content**

- PDF provenance and local semantic retrieval are implemented
- PDF / document
- Extract + clean / PyMuPDF
- Page chunks + / token-window embeddings
- Local embeddings / Sentence Transformers
- Vector storage / PostgreSQL + pgvector
- Semantic retrieval / Authorized sources
- Relevant context + citations
- Generator adapter
- Question + source links
- Real retrieval tested in Phase 9. Mock drafting uses keyword fixtures, not embeddings.

**Speaker notes**

PyMuPDF extracts text with page references. The ingestion splitter uses page-bounded character chunks, not a generator tokenizer. The local MiniLM embedding worker covers text through token windows and pools vectors; PostgreSQL/pgvector retrieves authorized chunks. Real offline CPU embedding and browser-to-retrieval were exercised in Phase 9. This is functional evidence, not a sustained hardware or retrieval-quality benchmark. Current mock drafting uses keyword-matched fixture text and does not invoke this embedding worker. Model files are local; startup checks their hashes without loading the model. Scanned PDFs need future OCR, and difficult tables/equations may extract imperfectly. Similarity and exact quotation alone do not prove truth. Sources: docs/materials.md, rag.md, generator.md; phase-9-completion.md.

## Slide 13 — Dual LLM architecture and current status

**Status:** ADAPTERS IMPLEMENTED • REAL INFERENCE NOT VALIDATED

**On-slide content**

- Hardware-validated model selection: pending • no LLM loaded
- Retrieved study context
- GENERATOR ROLE / Local adapter + mock
- Candidate MCQ
- VERIFIER ROLE / Local adapter + mock
- Stem + four options / Key + explanation / Difficulty + cognitive level / Source references
- Blind-answer stage, / then key / explanation critique. / Same checkpoint is not / independent-model evidence.
- Correctness + clarity / Distractors + grounding / Difficulty + explanation / Answerability + duplication
- ADVISORY
- PASS / REGENERATE / REJECT

**Speaker notes**

The generator contract returns stem, four options, key, explanation, difficulty, cognitive level and citations. The verifier workflow first solves without the proposed key/explanation, then critiques them. Separate prompts can reduce anchoring but do not guarantee independent errors. Current generator and verifier modes are mock. The guarded adapter candidate for both roles is qwen2.5:0.5b-instruct-q4_K_M; no weights were downloaded or run, and it is not a quality recommendation. Exact tags are environment-configured but unsupported tokenizer/template profiles fail clearly. Any later authorized trial must be CPU-only, bounded and sequential, unloading between roles. Gemini names from earlier diagrams are not used as local Ollama checkpoints. PASS/REGENERATE/REJECT is an advisory recommendation, not automatic release or a background regeneration loop. Sources: docs/generator.md, verifier.md, limitations.md; backend/app/config.py.

## Slide 14 — MCQ quality validation

**Status:** GATES IMPLEMENTED • ILLUSTRATIVE ARITHMETIC

**On-slide content**

- Generation alone does not establish eligibility for release
- 1  Schema validation
- ↓
- 2  Advisory verifier report
- ↓
- 3  Source grounding
- ↓
- 4  Duplicate detection
- ↓
- 5  Supported arithmetic checks
- ↓
- 6  Teacher review
- Independent math check
- 25% of 200 = 50
- Exactly one matching option required. / Missing or ambiguous answer: reject. / Unsupported math: hold for review.
- RELEASE ONLY IF ELIGIBLE
- Illustrative arithmetic. Mock ancestry blocks release even after a teacher edit.

**Speaker notes**

Schema checks establish structure. Advisory review examines the candidate but is not proof of truth. Source checks preserve exact evidence, duplicates are checked against a versioned comparison corpus, and supported arithmetic is calculated independently. The example 25 percent of 200 equals 50 is illustrative arithmetic, not a generated experimental result. The bounded validator does not execute arbitrary model code or prove general mathematics; unsupported expressions remain blocked from certification. Classroom release also requires teacher review and current evidence. Normal mock ancestry, stale versions, rejection, quarantine or missing real reports prevent release. Sources: docs/validation.md, teacher-review.md; backend validation implementation.

## Slide 15 — Adaptive learning engine

**Status:** IMPLEMENTED CANDIDATE POLICY • THRESHOLDS TO BE EVALUATED

**On-slide content**

- A deterministic candidate policy; learning benefit has not been measured
- Released answer evidence
- Topic / difficulty profile
- Eligible next private question

| Candidate policy | Implemented rule |
| --- | --- |
| Evidence | First exposure; submitted, released, approved items |
| Minimum coverage | 3 eligible observations at a difficulty level |
| Harder recommendation | Estimate ≥ 0.75 and last 3 correct at current level |
| Easier recommendation | Estimate ≤ 0.40 and at least 2 of last 3 incorrect |
| No eligible evidence / bank | Insufficient evidence / no recommendation |

- Thresholds are design assumptions, not experimental findings. Classroom tests stay fixed.

**Speaker notes**

bounded-performance-v1 replays eligible topic/difficulty evidence from the saved starting preference. Eligible evidence is first exposure, submitted, released and from an approved version; skips, expired attempts, repeated exposure and quarantined items are excluded. Each difficulty uses prior correct/incorrect counts of one and decay 0.95 per later eligible topic response. An estimate is (1 + decayed correct)/(2 + decayed responses); coverage needs three observations. At the current difficulty, promotion needs estimate at least 0.75 and the last three correct; demotion needs at most 0.40 and at least two of three incorrect. At most one level changes; absent coverage stays Insufficient evidence. The weighted topic index is not a standardized ability score. Recommendations require eligible unseen private questions; classroom sets stay fixed. User-supplied illustrative mastery percentages were removed to avoid implying results. Source: docs/attempts-and-adaptive.md.

## Slide 16 — Student feedback and quarantine

**Status:** IMPLEMENTED • NO AUTOMATIC RETRAINING OR REGRADING

**On-slide content**

- Reports trigger review; confirmed defects prevent new use
- Attempt + feedback
- Classify + aggregate
- Review weak questions
- Confirm defect / quarantine
- Review scores / correct version
- Fresh checks before new use
- REPORT CATEGORIES
- Wrong answer / explanation / Ambiguous / poor wording / Weak distractor
- Too easy / too difficult / Duplicate / Not from material
- Mathematical error /  / No automatic retraining / or historical regrading

**Speaker notes**

A student reports/rates an exact question version from their own completed attempt. The owner reviews comments and distinct-reporter counts; repeated reports do not prove a defect. Explicit confirmation quarantines the version, blocks future use and creates a score-review task. Original attempts and scores remain; affected solutions are withheld and the learning replay excludes defective evidence. Acknowledging review does not change scores or restore a version. Teachers create corrected versions with fresh checks and new assessments. Feedback does not automatically fine-tune model weights or change prompts. Triage defaults of three unresolved reporters and ratio 0.20 are design assumptions, not measured optimal thresholds. Sources: docs/feedback.md, analytics.md.

## Slide 17 — Reference-code assessment system

**Status:** IMPLEMENTED • EXAMPLE CODE IS NOT LIVE

**On-slide content**

- Explicit participant permission and server-side access checks
- TEACHER
- Create assessment
- Publish
- Generate unique code
- AI-ML-8F42K
- Illustrative code • not an active invitation
- Enter + validate
- Join + attempt
- Submit + results
- Expiry     Attempt limit     Time limit     Question and option randomization
- Mock drafts cannot be published. Native classroom checks used isolated synthetic evidence.

**Speaker notes**

Teachers publish only an eligible fixed set and receive a code to share. Students need both a valid code and active participant permission using their registered account. Expiry, maximum attempts, time limits, randomization, current release state and account authorization are rechecked. The displayed AI-ML-8F42K code is illustrative and not an active invitation. Codes are shown on issuance; replacement invalidates old codes. Closing permanently ends new access and triggers after-close result release. Native classroom acceptance used synthetic evidence in isolated databases because normal mock drafts correctly cannot be published. Sources: docs/assessments.md, attempts-and-adaptive.md; docs/evidence/phase-22-native-acceptance.json.

## Slide 18 — Technology stack and laptop fit

**Status:** NATIVE DEPLOYMENT VERIFIED • MOCK AI DEFAULT

**On-slide content**

- Free local core with a ₹0 service/subscription target

| Layer | FREE / OPEN SOURCE local core |
| --- | --- |
| Frontend / backend | React + Vite + Tailwind; Python + FastAPI |
| Data / documents | PostgreSQL 18.4 + pgvector 0.8.7; PyMuPDF; local PDFs |
| Retrieval | Sentence Transformers + local MiniLM; direct Python |
| AI roles | Mock default; guarded Ollama adapters; no LLM loaded |
| Validation / security | Pydantic + exact Python arithmetic; JWT + Argon2 |
| Operation | Local startup, restricted DB roles, backup / separate restore |

- 8 GB RAM, CPU only • Hardware-validated model selection: pending
- ₹0 service target. Free proprietary C++ build tools compiled pgvector; no paid API.

**Speaker notes**

The runtime is local and free/open source: React/Vite/Tailwind, Python/FastAPI, PostgreSQL/pgvector, PyMuPDF under AGPL, Sentence Transformers/MiniLM, Pydantic, PyJWT and Argon2. Direct Python orchestration is used; LangChain is not required. SymPy is installed as a dependency but active mathematical release checks are bounded exact Python arithmetic. Ollama adapters exist but the normal launcher refuses non-mock modes and does not start Ollama. PostgreSQL 18.4 and pgvector 0.8.7 were exercised natively; the approved Microsoft C++ build tools are free proprietary build-time software. The laptop has 8 GB RAM, i5-1035G1 and integrated Intel graphics. Real model selection and sustained memory/latency remain pending. The ₹0 claim excludes existing hardware, electricity and internet. Sources: docs/setup-guide.md, phase-22-completion.md and dependency lockfiles.

## Slide 19 — Database design and provenance

**Status:** IMPLEMENTED • 12 MIGRATIONS / 15 GRANT FILES

**On-slide content**

- Immutable versions connect sources, attempts and feedback
- Users
- Materials / Documents + chunks
- Questions + versions / Options + source links / Verification records
- Assessments / Question-version links / Reference codes
- Attempts / Answers
- Student profiles / Derived topic evidence
- Feedback / Question-version reports
- Analytics / Derived from attempts
- Ownership, version links and foreign keys preserve provenance and reproducible scoring.
- 12 migrations + 15 grant files applied. Topic mastery is derived; its cache table is reserved.

**Speaker notes**

Users own private material/document/chunk records and question versions. Assessments pin exact versions; attempts save option permutations and answer state. Verification, deterministic validation, teacher decisions and release records form the evidence chain. Feedback refers to exact versions/attempts. The diagram is a simplified relationship view, not all fields/tables. Student profiles store preferences; current topic profiles are derived from eligible mastery_evidence, while topic_mastery remains reserved for a future cache. Analytics derive from authoritative attempts rather than competing mutable score totals. All 12 migrations and 15 grant sets were applied to the dedicated native cluster. Runtime login is restricted; backend ownership filters scope users. Sources: docs/database.md, attempts-and-adaptive.md, phase-22-completion.md.

## Slide 20 — Evaluation harness and planned studies

**Status:** HARNESS IMPLEMENTED • REAL EVALUATION PLANNED

**On-slide content**

- Synthetic engineering checks are separate from AI and learning experiments
- A: Topic baseline
- B: Frozen RAG context
- C: Verify same B item
- D: Add math gate
- Item quality
- Correctness • answerability / Grounding • relevance / Distractor quality
- Pedagogical quality
- Difficulty agreement / Diversity • complexity / Duplicate rate
- System / learner study
- Latency • retention / rejection / Satisfaction • learning benefit / Separate adaptive comparison
- Implemented: synthetic harness, evidence export and blinded human-review packs
- Planned: real model trials, independent ratings and learner study. Results: To be evaluated.

**Speaker notes**

The implemented matched harness has A topic-only generation, B generation with frozen local RAG context, C verification of that exact B candidate, and D bounded math validation of the same candidate. C/D do not regenerate easier replacements; failed/rejected candidates stay in the evidence, exposing retained yield. Website runs are synthetic only. The deliberate mock numerical error tests rejection plumbing, not verifier reliability. Human-review packs and a rubric are available, but no completed independent real-item ratings exist. Measure correctness, answerability, relevance, grounding, distractors, difficulty agreement, diversity, complexity, duplication, latency and rejection denominators. A separate controlled learner study is required for satisfaction and adaptive learning benefit; the current ablation does not measure the complete adaptive system. Sources: docs/evaluation.md; evaluation/RUBRIC.md.

## Slide 21 — Verified engineering evidence and contribution

**Status:** RECORDED PHASE 22 EVIDENCE • ALL CLASSROOM DATA SYNTHETIC

**On-slide content**

- Local workflow acceptance supports implementation claims, not AI accuracy
- 58 passed
- Targeted Phase 22 regressions
- 14 passed
- Native classroom browser checks
- Restore passed
- Records + 3 PDF hashes matched

| Engineering contribution | Evidence boundary |
| --- | --- |
| Versioned review + access + feedback | Implemented; synthetic workflow acceptance |
| Native data + recovery + handover | Implemented and locally exercised |
| RAG + AI roles + bounded validation | Retrieval tested; real LLM quality unvalidated |
| Adaptive policy + evaluation tooling | Implemented candidate; learner effects unmeasured |

- Integration contribution; no claim of new algorithms or superiority over the paper.

**Speaker notes**

Phase 22 passed 58 targeted regression checks, including deployment, launcher, configuration and database boundaries. Its native classroom journey passed 14 browser checks. The eight grouped acceptance checks include that journey; do not sum groups as independent samples. An additional embedded journey passed 14 checks. Native transactions used independent connections and bounded row-lock contention. Immediate database restart preserved application fingerprints. Full database/PDF backup restored separately: all non-session table fingerprints and three PDF hashes matched; sessions were revoked and fresh login worked. Phase 21 separately recorded 288 backend tests, 115 frontend tests, 51 foundation browser checks and 14 classroom checks, with a real embedding test skipped. These are historical engineering results, not new Phase 24 runs or a statistical research sample. Our contribution is the auditable local integration. Sources: docs/phase-21-completion.md, phase-22-completion.md and evidence/phase-22-native-acceptance.json.

## Slide 22 — Conclusion and future scope

**Status:** FINAL HANDOVER • REAL AI / LEARNER RESULTS TO BE EVALUATED

**On-slide content**

- The local engineering deliverable is complete; research validation remains open
- Local platform implemented and tested / Real AI quality and learning gains: To be evaluated
- FUTURE SCOPE
- Hardware-approved local model trials / Independent MCQ ratings and learner studies / Broader math, question types and languages
- Question-bank / recovery screens / Calibrated learner modelling / OCR and multimodal questions
- Thank You
- Questions & Discussion

**Speaker notes**

We have implemented and documented the local assessment platform, its permission and quality gates, candidate adaptation, feedback/quarantine, evidence harness and recovery workflow. The 24-phase roadmap closes with this final-review evidence update; that does not mean every feature in the original research vision is finished. Default AI remains mock. Future work includes an explicitly hardware-approved small-model trial, independently rated real MCQs, calibrated adaptation and learner studies. Dedicated question-bank/recovery browser screens, broader mathematics, OCR, languages and multimodal questions remain deferred. No measured superiority over MCQGen or validated learning gain is claimed. Thank you; questions and discussion. Sources: docs/limitations.md, project-progress.md, phase-22-completion.md and Phase 24 evidence record.

