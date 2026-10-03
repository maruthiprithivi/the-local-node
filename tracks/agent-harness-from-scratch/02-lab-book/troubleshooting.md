# Diagnose the harness before changing it

Start with the stop reason and last completed trace event. Separate a model suggestion from a policy decision and an observed side effect. Repeating a command is safe only when its state/effect contract says so.

| Symptom | Inspect | Next step |
| --- | --- | --- |
| `No module named course_harness` | Interpreter, active environment, current lab directory | Use the same environment for editable installation and execution. |
| No selected pytest cases | Lesson selector and delivered tests | Inspect test names; do not interpret “no tests” as a pass. |
| Fake replies differ | Fixture identity, modified files, clock injection | Restore controlled inputs on your own branch; avoid live providers. |
| Unknown tool/type error | Registry name, exact argument shape, unexpected fields | Correct the request contract; do not loosen validation globally. |
| Approval keeps waiting | Pending operation, scope, target, content digest | Approve the exact reviewed action through the supported path. Never edit stored approval rows to bypass policy. |
| Permission denied after approval | Changed arguments/precondition or host policy | Re-review the changed proposal; an earlier approval is intentionally stale. |
| Budget exhausted | Steps, tool calls, retries, output, remaining deadline | Find repeated work before increasing a ceiling. |
| Stale SRE evidence | Observation time and source | Gather a fresh permitted observation; do not restart based on an old graph. |
| Runner timed out | Started/completed/uncertain state and process cleanup | Observe actual fixture state before considering another action. |
| Queue full | Capacity and admission decision | Respect reject/delay/coalesce policy; inspect old tasks rather than deleting them blindly. |
| Task stranded after crash | Lease, action journal, human stop | Recover the claim separately from reconciling any started effect. |
| Restart does no work | Persisted human stop and paused approvals | Inspect and intentionally resume through documented controls. |
| Optional provider authentication error | Required environment variable, provider config | Fail before request; never print the key. |
| Unsupported provider feature | Declared capability and fixture protocol | Choose a supported explicit configuration; do not silently downgrade. |

## Three recovery walk-throughs

Coding: a patch preview was approved, but another writer changed the file. The digest mismatch is the expected protection. Read the new file, generate a new diff, and obtain approval for that new action.

SRE: a restart was started, the run timed out, and health is unknown. Observe service state with a read-only tool. Record “completed” only if evidence supports it; otherwise retain uncertainty or escalate. More retries do not establish truth.

Automation: an artifact exists but the completion event is missing. Compare its content and identity with the action's expected postcondition. Resolve the journal entry before releasing that event for execution again. A queue lease and an effect record answer different questions.

## Asking for useful help

Include the course commit, Python/platform versions, checkpoint/scenario, redacted stop reason, and the smallest synthetic fixture that reproduces the problem. Include actual exit status. Do not paste credentials, personal repositories, or production incident logs. State whether tests were run or only source was reviewed.

