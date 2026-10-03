# Lesson 32: separate harness collaboration — narration script

Readable script; no recording or multi-host demonstration is claimed. Caption
future narration and describe every state and arrow aloud.

Separate harnesses have separate controllers, providers, policies and executors.
Describe the path from a scoped authenticated task envelope to the coordinator,
then to the SRE receiver's bounded read lease, then back to a recorded result.
Describe automation's independent policy/approval check before a follow-up.

Open team.py and trace TaskEnvelope, receive_task, claim_task, receive_result and
recover_tasks. Point out the idempotency key, causal sequence, capability
intersection, deadline, budget and increasing fencing token. Shared memory gives
evidence; it does not give ownership of a task.

Run the checkpoint on an approved host and inspect actual IDs and receipts.
Label all identities, transports and effects as fixtures. Withhold an
acknowledgment and replay the identical result; distinguish receipt replay from
executing work again. Advance the injected clock, recover the task, and try a
stale owner result. Explain why the journal rejects it and why any real external
executor would need to enforce the fence too.

Pause for the coding-to-SRE evidence request and approved automation follow-up
exercise. Give hints about local reauthorization, narrowed capabilities and
observation before retry. Ask: why isn't shared memory a task lock, and what
evidence permits reconciliation after a possible effect?

Continue with one small reversible extension. Multiple processes, authenticated
network transport and multi-host deployment remain future hardening, not claims
from the deterministic single-host fixture tests.

