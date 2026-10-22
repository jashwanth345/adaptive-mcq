# Phase 18 — analytics

13 October 2026. Scope: R22, R25 and a teacher-only optional classroom ranking (R26).

- Read-only, ownership-scoped PostgreSQL aggregation over authoritative attempt snapshots and answers. No score cache, model calls or invented data.
- Student summaries include only released, completed results. Teacher summaries include owned classroom assessments, including results withheld from students.
- Original scores remain intact after quarantine. Accuracy/breakdowns exclude questions no longer approved. Correct, incorrect, skipped and excluded counts remain separate; zero denominators produce no percentage.
- Repeated and expired attempts count in operational analytics, not independent mastery evidence. Link to the existing provisional learning profile for recommendations.
- Attempt elapsed time includes idle time and is capped at a timed attempt's deadline. Per-question response time is unavailable. Overdue unfinalized attempts stay pending; analytics never grades them.
- Teacher assessment filter, topic/difficulty/type breakdowns, most missed items, feedback counts, paginated history and an optional teacher-only best-submitted-attempt ranking. No public/student peer leaderboard or cross-course ranking.
- Verify authorization, embargoes, quarantine, repeated attempts, denominators, pagination and responsive empty/populated screens. Research evaluation remains Phase 19.
