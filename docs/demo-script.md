# Final-review demonstration script

Suggested duration: **8–10 minutes**, plus questions. This is a script and preparation checklist, not a new recorded demonstration or experimental result. Use the [current limitations](limitations.md) in your spoken claims. Use the completed [Phase 24 review deck](../../Adaptive_MCQ_Final_Review_Phase24_Final.pptx).

## Prepare before faculty arrive

1. Start the prepared project and use accounts you control. Do not show passwords or create shared default accounts. Keep teacher and student sign-ins in separate browser contexts if needed; a refresh requires sign-in again.
2. Prepare one short authorized text PDF with a recognizable topic. Use a copy of benign study material, without personal data. Open it in Study materials in advance and confirm extraction. Keep a small test draft ready in case the live upload is slow.
3. Keep mock generator/verifier enabled. Do not install or start an LLM. Pre-open the screenshots/evidence linked below for the classroom segment; they are synthetic test evidence, not live accounts in the retained database.
4. Close unnecessary applications. Do not run integration suites, embedding preparation, native crash acceptance or backup restore during the presentation. Semantic retrieval is optional on this 8 GB laptop; the core live script does not require model inference.
5. Check that the screen contains no private operator configuration, participant email list or unapproved personal data. Use synthetic records when discussing recorded scores.

## Run of show

| Time | Show / action | Suggested explanation and expected state |
|---|---|---|
| 0:00–0:45 | Sign-in and Teacher dashboard | “Our project implements a local assessment platform with teacher control and student workflows. This laptop demonstration uses labelled mock AI. Real MCQ quality and learning gains have not been measured.” Empty counts are acceptable; never substitute invented totals. |
| 0:45–1:30 | Create/open a course and add a topic | “The teacher organizes the course; ownership checks keep workspaces separate.” Show a saved course/topic rather than a static concept image. |
| 1:30–2:30 | Study materials: upload/open the small PDF and show a page passage | “Text extraction retains page provenance. RAG can index this source locally and retrieve relevant passages. Extraction and retrieval do not prove the source is correct.” If skipping live embeddings, state that explicitly. |
| 2:30–3:30 | Generate MCQs: choose the source/topic and Create test draft | “The generator interface produces a structured draft. Today this is a deterministic fixture with placeholder distractors, not an LLM result.” Show options, explanation and exact source quotation. |
| 3:30–4:30 | Verification/validation and Teacher review | “Separate review and validation stages record evidence. Versioned edits preserve history. Mock content stays blocked from approval and publication, even after a teacher edit.” Show the blocker; do not try to override it. |
| 4:30–5:15 | Assessments: save/open an unpublished draft | “Publication needs eligible questions, explicit participant permissions and a reference code. This draft cannot be published with mock questions.” Explain that the next segment uses previously recorded synthetic integration tests. |
| 5:15–6:30 | Recorded classroom player/results screenshots and Phase 22 evidence | “These screenshots show the actual UI with synthetic test accounts. The native browser checks exercised joining, saved answers, API restart/retry, grading, feedback and analytics. These are engineering checks, not classroom research.” |
| 6:30–7:15 | Student dashboard, My learning and My analytics | “The student sees only released own outcomes. Adaptation is a provisional evidence-based rule for private practice; classroom assessments remain fixed. Empty or insufficient-evidence states are intentional.” |
| 7:15–8:15 | Evaluation lab: Run synthetic smoke check or reopen one | “The framework preserves matched inputs and rejection evidence. This fixture deliberately includes a math error to exercise validation. It does not measure LLM accuracy.” Show To be evaluated fields. |
| 8:15–9:00 | Phase 22 completion and limitations | “The local database, separate backup/restore and startup passed acceptance. The final evidence/presentation package is complete. Actual LLM selection, independent human ratings and learning studies remain pending.” |

Do not promise a question count, latency or numeric score in the script. Show whatever was actually saved. If the demo fails, describe the failure and use labelled recorded evidence; do not present a screenshot as a live action.

## Recorded evidence to keep ready

- [Teacher dashboard](images/phase-20-teacher-dashboard-desktop.png) and [student dashboard](images/phase-20-student-dashboard-desktop.png).
- [Assessment player](images/phase-20-assessment-player-desktop.png) and [recorded results](images/phase-20-assessment-results-desktop.png).
- [Feedback review](images/phase-17-feedback-review-desktop.png), [learning screen](images/phase-16-learning-desktop.png), [evaluation lab](images/phase-19-evaluation-desktop.png).
- [Phase 22 completion](phase-22-completion.md), [native acceptance record](evidence/phase-22-native-acceptance.json), [startup record](evidence/phase-22-native-startup.json).

These existing screenshots predate native Phase 22 deployment and use synthetic fixtures. The native JSON report separately records the later native checks. Do not claim that an earlier screenshot was captured from a real student cohort or that it establishes model correctness.

## Short faculty answers

**Is this a working dual-LLM system?** Separate generator and verifier adapters/contracts and downstream gates are implemented. The supplied laptop uses mocks; real inference and independent-checkpoint verification have not been validated. Gemini names in early diagrams were superseded by the local-only requirement and are not used as local models.

**Why demonstrate a blocked publication?** A release gate that accepts mock evidence would make the demonstration misleading. The positive classroom path was tested with isolated synthetic fixtures; normal mock drafts deliberately cannot be published.

**What does feedback change?** It creates version-specific reports and owner review. Confirmed defects quarantine future use and exclude affected learning evidence. Feedback does not fine-tune model weights or silently rewrite historical scores.

**How is adaptation evaluated?** The candidate policy replays eligible released first-exposure evidence and adjusts private-practice difficulty. Thresholds and learning benefit remain to be evaluated; operational analytics are not proof of learning improvement.

**What is the contribution?** A locally executable integration of provenance, separate generation/review roles, bounded validation, teacher decisions, assessment access, feedback/quarantine and evidence tooling. We claim implemented engineering mechanisms, not unprecedented research novelty or measured superiority over MCQGen.

**What is next?** Phase 24 has completed the final presentation/evidence package. Separate future work includes hardware-approved model trials, independent ratings, learner studies and the explicitly deferred features.
