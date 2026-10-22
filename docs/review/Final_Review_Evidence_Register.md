# Final-review evidence register — Phase 24

Updated 15 October 2026. Use this register to distinguish existing research, implemented software, synthetic engineering evidence and future research. It accompanies the [current 22-slide deck](Adaptive_MCQ_Final_Review_Phase24_Final.pptx), [slide content/speaker notes](Presentation_Content_and_Speaker_Notes_Phase24.md) and [speaking/viva guide](Viva_and_Review_Guide_Phase24.md).

## Claim-to-evidence map

| Slides | Claim / artifact | Source and evidence status |
|---|---|---|
| 1 | Institution, team, guide, course and academic year | Supplied abstract image and user requirements. Names preserved: V. NaveenKumar, V. Jashwanth, G. Sai Koushik, P. Theja Bhuvan Reddy; Dr. D. Kavitha, Associate Professor, Dept. of CSE (AI & ML). |
| 2–4 | MCQGen method, study scope and limitations | Supplied Hang, Tan and Yu IEEE Access paper, 2024, DOI [10.1109/ACCESS.2024.3420709](https://doi.org/10.1109/ACCESS.2024.3420709); Sections III–VII. 60 questions, three lecturers/three model evaluators and two-student learning example belong to the paper. |
| 5–7 | Local platform and evidence-controlled integration | [Current limitations](adaptive-mcq/docs/limitations.md), [user guide](adaptive-mcq/docs/user-guide.md). Mechanisms implemented; superiority and educational benefit unmeasured. |
| 8 | Actual teacher/student frontend | [Teacher capture](adaptive-mcq/docs/images/phase-20-teacher-dashboard-desktop.png), [student capture](adaptive-mcq/docs/images/phase-20-student-dashboard-desktop.png). Cropped within the slide; synthetic Phase 20 accounts/records, not real students. |
| 9–10 | Teacher/student workflow and release policy | [Teacher review](adaptive-mcq/docs/teacher-review.md), [assessments](adaptive-mcq/docs/assessments.md), [attempts/adaptation](adaptive-mcq/docs/attempts-and-adaptive.md). Positive classroom paths use isolated synthetic evidence; ordinary mock drafts remain blocked. |
| 11–12 | Architecture and local retrieval | [RAG guide](adaptive-mcq/docs/rag.md), [Phase 9 evidence](adaptive-mcq/docs/phase-9-completion.md), [deployment guide](adaptive-mcq/docs/local-deployment.md). Real retrieval tested earlier; no new embedding inference in Phase 24. Mock drafting uses keyword fixtures. |
| 13 | Separate generator/verifier contracts | [Generator](adaptive-mcq/docs/generator.md), [verifier](adaptive-mcq/docs/verifier.md). Guarded local adapter candidate remains unvalidated. No LLM weights downloaded or executed. Same-checkpoint roles are not independent models. |
| 14 | Validation and release gates | [Validation](adaptive-mcq/docs/validation.md), [teacher review](adaptive-mcq/docs/teacher-review.md). Arithmetic shown is an illustrative calculation. General symbolic/formal mathematics is not implemented. |
| 15 | Candidate adaptive rules | [Policy contract](adaptive-mcq/docs/attempts-and-adaptive.md). Minimum coverage and thresholds are implemented design assumptions, not measured optimal values. Original illustrative mastery percentages were removed. |
| 16 | Feedback, quarantine and score-review behavior | [Feedback](adaptive-mcq/docs/feedback.md). Confirmed defects block new use; original scores persist. No automatic fine-tuning or retroactive regrading. |
| 17 | Reference-code access and attempt controls | [Assessment guide](adaptive-mcq/docs/assessments.md), [native acceptance](adaptive-mcq/docs/evidence/phase-22-native-acceptance.json). Displayed code is illustrative, not live. |
| 18–19 | Actual stack, native data and provenance | [Setup](adaptive-mcq/docs/setup-guide.md), [database](adaptive-mcq/docs/database.md), [installation evidence](adaptive-mcq/docs/evidence/phase-22-installation.json). 12 migrations and 15 grant files applied; current topic profiles are derived, not a populated mastery cache. |
| 20 | Evaluation tooling and planned metrics | [Evaluation guide](adaptive-mcq/docs/evaluation.md), [rating rubric](adaptive-mcq/evaluation/RUBRIC.md). Synthetic A/B/C/D filtering ablation exists; real human/AI experiments and a separate adaptive learner trial remain planned. |
| 21 | Native application verification and contribution | [Phase 22 completion](adaptive-mcq/docs/phase-22-completion.md), [native acceptance](adaptive-mcq/docs/evidence/phase-22-native-acceptance.json), [startup evidence](adaptive-mcq/docs/evidence/phase-22-native-startup.json). Engineering evidence only. |
| 22 | Delivery boundary and future work | [Project progress](adaptive-mcq/docs/project-progress.md), [limitations](adaptive-mcq/docs/limitations.md), [Phase 23 handover](adaptive-mcq/docs/phase-23-completion.md). Roadmap closure does not eliminate declared research/feature deferrals. |

## Recorded results and how to quote them

| Recorded run | Actual result | Interpretation |
|---|---|---|
| Phase 9 retrieval | Real offline CPU embeddings and browser-to-pgvector retrieval exercised | Functional retrieval evidence; not a sustained laptop benchmark or MCQ-quality study |
| Phase 20 SQL/migration checks | 119 SQL checks and seven migration-runner checks | Historical schema/integration evidence; not rerun in Phase 24 |
| Phase 21 wider regression | 288 backend, 115 frontend, 51 foundation browser and 14 classroom browser checks passed | One real-embedding test intentionally skipped. Final seven upload checks overlap the backend suite. These suites are not independent research samples |
| Phase 22 targeted regression | 58 passed | 24 deployment, two launcher, 26 configuration and six database checks |
| Phase 22 native classroom journey | 14 passed | Synthetic publication/admission, saved answers, restart/retry, release, analytics, feedback/quarantine and study export |
| Phase 22 embedded classroom regression | 14 passed | Compatibility regression after fixture adaptation, separate from the native journey |
| Phase 22 native acceptance | Eight grouped checks passed | The native browser journey is included in those groups; do not add the groups to a test-sample denominator |
| Native backup/restore | All non-session application table fingerprints and three PDF hashes matched; restored sessions revoked; fresh sign-in worked | Separate synthetic restore target; no live cutover, full-machine power-loss test or real user-data migration |
| Retained native startup | Frontend/API proxy, login route, security headers and child shutdown passed | Prepared mock-mode local stack; no LLM inference |
| Phase 23 documentation | 78 Markdown files, 458 local link targets, 16 routes and three launchers checked | Historical documentation snapshot; not an application regression suite |

Sources: [Phase 9](adaptive-mcq/docs/phase-9-completion.md), [Phase 20](adaptive-mcq/docs/phase-20-completion.md), [Phase 21](adaptive-mcq/docs/phase-21-completion.md), [Phase 22](adaptive-mcq/docs/phase-22-completion.md), [Phase 23](adaptive-mcq/docs/phase-23-completion.md). Do not add overlapping runs together and call the sum “accuracy,” a student sample or independent experimental observations.

## Presentation changes from the proposal

- Retained the 22-slide order, academic identity and original navy/teal/purple visual design; edited the imported native slide objects.
- Replaced “no implementation supplied” with precise implemented/mock/planned status and verified engineering evidence.
- Replaced concept dashboard wireframes with actual labelled synthetic UI captures.
- Replaced the obsolete larger-model candidate names and illustrative mastery chart with the current adapter boundary and candidate policy rules.
- Corrected planned durable queue, broad SymPy validation, automatic prompt updates and mastery-cache implications to current behavior.
- Distinguished the implemented A/B/C/D filtering harness from a future complete adaptive-system learner experiment.
- Preserved the earlier proposal deck and notes for historical traceability; use the **Phase24** files for the final review.

## Claims that remain unavailable

No real AI factual-accuracy, answerability, distractor-quality, diversity, model-latency or hardware-inference result. No completed independent human rating study, actual learner-satisfaction score, learning-gain result or statistically supported superiority over MCQGen. No evidence that the 8 GB laptop supports simultaneous models. No supporting 2025 research paper was supplied for the abstract's “2025 system” statement.

The private runtime configuration/operator credentials, real uploads and operational database are excluded from this public review package. Use [current documentation](adaptive-mcq/docs/README.md) and the [demo script](adaptive-mcq/docs/demo-script.md) to present the actual scope.
