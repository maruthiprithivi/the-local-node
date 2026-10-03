# Lesson 31: Multiple users and central memory — narration script

Readable script; no recording is claimed. Caption future narration and describe
all diagram arrows and state changes in words. Keep the canonical lab open for
exact APIs, commands, hints and the separate solution.

## Opening

Two simulated authenticated users share selected facts through one local service boundary. Personal scope belongs to the authenticated caller. Publishing requires an explicit owner choice and authorized team membership. Check access before retrieval reaches a provider. Retain owner, provenance, expiry and version; optimistic edits surface conflict. Revocation blocks future access and deletion invalidates published descendants.

## Diagram description

The service verifies the caller and scope before touching content. An owner explicitly publishes one record; other private records remain unavailable.

## Source walkthrough

Open team.py and Authenticator.authenticate/verify; TeamBoundary put_memory/read_memory/inspect_memory/publish_memory/delete_memory; host membership administration. Follow the concrete host decision before
implementing the learner TODO. Use publish_memory and preserve its explicit consent argument; never publish a full transcript by default.

## Successful path

Say: A authenticated -> private convention + private preference.

Say: A consents to convention publication -> team version1.

Say: B reads team convention; B cannot inspect A private preference.

Say: B stale expected_version -> conflict, no overwrite.

Say: membership revoked -> future read rejected; delete origin -> shared descendant absent.

Pause to inspect the actual checkpoint evidence and distinguish semantic narration
from literal output. Identify every simulated identity, effect and receipt.

## Failure and learner pause

Construct AuthContext('alice', permissions) directly instead of using Authenticator.authenticate. The boundary rejects it. Write the same shared key with expected_version=0 after version1 exists: reject conflict. Revoke B's membership and verify future access fails even if B saw the earlier value.

User A shares a toy project convention with B while retaining a private preference. B proposes a conflicting correction; inspect version history, reconcile explicitly, revoke B and delete the original. Add read/search/write/delete leakage tests and a cached-deletion case.

Ask learners to predict the state/effect count, then write the test. Give the
progressive hints one at a time before showing the solution.

## Explain and continue

Why is prompt-only filtering too late? What does revocation protect, and which information cannot be recalled after disclosure?

Add a real authenticated service interface in a separately hardened environment. A SQLite file is not a distributed central memory service and must not be shared across hosts.

