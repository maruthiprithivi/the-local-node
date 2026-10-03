# Lesson 30: A GitHub mention becomes bounded draft work — narration script

Readable script; no recording is claimed. Caption future narration and describe
all diagram arrows and state changes in words. Keep the canonical lab open for
exact APIs, commands, hints and the separate solution.

## Opening

Replay @course-harness against FakeGitHub and a durable queue. Verify the raw-body HMAC fixture signature before JSON parsing; obtain actor/comment data from the fresh fake API record. Gate repository, fork, command, permission and exact base. Produce one isolated fake branch/diff, synthetic check receipt and exact publication approval before a fake draft PR. No live webhook, app, secret or paid call is created.

## Diagram description

Authentication precedes command parsing. One bounded durable task produces reviewable evidence. Publication is a separate exact approved action and never a merge.

## Source walkthrough

Open extensions.py and MentionReceiver.receive/prepare_next/publication_digest/publish/reconcile_publication; FakeGitHub; examples/github/. Follow the concrete host decision before
implementing the learner TODO. Serialize the synthetic sender's event and call receive with its fixture signature. Do not pass an actor ID in JSON.

## Successful path

Say: signed permitted fix -> admitted task_id=1.

Say: redelivery -> duplicate task_id=1.

Say: prepare_next -> fake_branch_diff + synthetic_check_receipt + digest.

Say: publish exact fresh approval -> one fake draft PR, merged=False.

Say: lost acknowledgment -> uncertain -> find existing PR -> reconcile.

Pause to inspect the actual checkpoint evidence and distinguish semantic narration
from literal output. Identify every simulated identity, effect and receipt.

## Failure and learner pause

Set the fresh fake actor's permission to read, use a fork or stale base, or mutate the signed body. No task should enter privileged work. Then simulate ambiguous_publish=True: one fake PR exists, task becomes uncertain, and reconcile_publication discovers it instead of creating another.

Replay one bug-fix event twice, inspect the bounded diff/check receipt, and publish only after reviewing its exact digest in the fixture. Replay an unauthorized mention. Add changed/deleted comment, access revocation, cancel, expired approval, stale base, bot-loop and rate-limit cases; report any unsupported live behavior.

Ask learners to predict the state/effect count, then write the test. Give the
progressive hints one at a time before showing the solution.

## Explain and continue

Why isn't an @mention a permission grant? Which fixture value represents authentication, and what must replace it in a real deployment?

Study the actual Claude action and security guide linked in advanced-extensions.md. A separately reviewed live setup needs real auth, least-privilege grants, exact base trust and bounded spending. Inactive templates are examples only.

