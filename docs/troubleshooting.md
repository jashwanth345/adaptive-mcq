# Troubleshooting

Use the prepared [startup steps](setup-guide.md) first. Record the screen message, time and safe request ID if shown. Do not include passwords, bearer tokens, `.env`, operator credentials or private student/PDF contents in a support message.

## Startup and accounts

| Symptom | Likely meaning and action |
|---|---|
| Website will not open | Keep the Start-Project terminal open and wait for Ready. Use localhost:5173, not a network address. If startup failed, inspect its message before trying again. |
| Database unavailable | Run `deployment.native start` from the project folder. This project's database is on 55432, not the installed service's usual 5432. Check the private operator log locally if it fails. Do not initialize a replacement cluster or change unrelated service settings. |
| Port already in use | Another project instance or service may own it. Stop the known project terminal normally. Do not terminate every Python/Node process. Run doctor with the website stopped. |
| Secret/configuration error | Existing `.env` must remain private and intact. Stale process environment settings override it. Ask the local operator to inspect setting names/overrides without printing values. Do not regenerate JWT secrets as a routine repair. |
| Missing pgvector, schema or grants | Use the matching project release and all 13 migrations/15 grant files. The prepared cluster already has these. Have the operator investigate the actual instance/role before applying anything; back up first. Never edit applied SQL or grant administrator rights to the API. |
| Missing build/dependency/model snapshot | Restore the matching prepared assets or follow fresh-machine preparation. Startup never downloads them. A missing embedding snapshot does not mean an LLM is required. |
| Sign-in disappears after reload | Expected memory-only token behavior. Sign in again; saved database records remain. Unsaved forms are not persistent. |
| Teacher navigation absent | Select Teacher when creating a new account. Both roles share login. Re-registering an existing student email cannot promote it; existing-account role changes still require the trusted operator. |
| Duplicate email | Sign in with the existing account. Teacher creation does not silently promote an existing student. The operator can use the documented grant-teacher command if appropriate. |
| Forgotten password | No email/reset-link feature exists. Do not expect a reset message. Preserve the account's data and contact the local operator; this release has no implemented operator password-reset command either. A replacement account does not inherit the old account's private data. |
| Too many attempts / 429 | Wait for the indicated retry time. Login limits include successful attempts and persist across API restarts. Avoid repeated rapid retries during demonstrations. |

## PDFs, drafts and classroom operations

| Symptom | Action |
|---|---|
| PDF rejected | Use an unencrypted PDF within the displayed limits. Windows scans use the installed offline OCR language; split scans longer than 10 scanned pages. If OCR is unavailable, use a PDF with selectable text or have the operator check the Windows OCR language. Complex layouts/equations may extract poorly; compare passages with the original. |
| PDF processing time limit | Text extraction is bounded to 30 seconds and the separate offline OCR worker to 45 seconds; the browser allows 120 seconds for the whole upload. Close heavy applications and retry or split the PDF. Failed workers are terminated and temporary page images are removed; no incomplete material record is saved. |
| Re-upload shows old title | Same-owner identical file bytes reuse the saved record; the first title is retained. This prevents duplicate storage after retry. |
| Search busy, slow or out of memory | Process one small document at a time, close unnecessary apps, and stop retrying concurrently. An indexing failure is not evidence of poor subject knowledge. Skip live semantic retrieval on a memory-constrained demo; mock drafting does not require it. |
| No relevant draft passage | Choose a topic actually present in the selected PDF. Default keyword test retrieval is not semantic RAG. Do not invent a passage or change the evidence record. |
| Placeholder distractors / test report | Expected mock output. It checks software flow and cannot be used as educational-quality AI content. |
| Approval or publication blocked | Read the exact blockers. Mock origin, stale version/report/corpus, quarantine, rejection or missing real evidence are legitimate failures. Editing cannot remove mock ancestry. Do not bypass the gate. |
| No reference code shown later | Codes are shown on issuance/successful same-request retry, not ordinary detail reads. An eligible assessment's owner can issue a replacement and share it with permitted students. |
| Valid-looking code does not admit student | Check registered account/role, explicit participant permission, expiry/replacement/revocation, remaining attempts and assessment/question state. Course membership or knowledge of a code alone is insufficient. |
| Results are withheld | The assessment may release only after closure. Ask the teacher; this is an enforced policy, not a missing-score calculation. |
| Save conflict or uncertain submission response | Avoid simultaneous editing tabs. Reopen the attempt to inspect the server state. Retry the same operation through the existing UI, which retains request keys; do not create a new attempt merely because a response was lost. Unsaved work after a deadline cannot replace saved answers. |
| My learning has no recommendation | New accounts, insufficient eligible evidence or no approved unseen private questions can legitimately produce this state. Mock drafts cannot fill the eligible bank. |
| Score unchanged after defect confirmed | Quarantine preserves original scores and flags them for review. Acknowledgement is not automatic regrading. Corrected versions belong in new assessments. |
| Counts/analytics unavailable | Retry after checking database readiness. Error states must not be read as zero activity. “No data” can also be a legitimate empty/release-filtered result. |

## Recovery escalation

After a crash, stop known project processes normally if possible, start the dedicated database, run doctor with website ports free, and follow [reconciliation and restore](local-deployment.md). Saved attempt answers survive normal API restart; unsaved browser selections are not covered.

Do not delete a PDF just because its upload response failed. It may be committed and referenced. Reconciliation is read-only; missing/corrupt files require a matching verified backup. Incomplete backup/restore output is retained for inspection and must not be presented as successful. A passing checksum check is not a substitute for a separate restore rehearsal.

Do not run `deployment.native_acceptance` as a troubleshooting command on active user data. It includes an immediate database stop and is guarded against accounts in the normal application database. Do not remove that guard. Routine Phase 23 use does not need any crash experiment.
