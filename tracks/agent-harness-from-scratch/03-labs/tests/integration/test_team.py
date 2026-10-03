"""Offline two-user/service integration; no sockets or shared multi-host SQLite."""
from dataclasses import replace
import pytest

from course_harness.team import AuthContext, Authenticator, TaskEnvelope, TeamBoundary, TeamError, checkpoint

PERMISSIONS = frozenset({"memory:read", "memory:write", "memory:delete", "memory:publish",
                         "task:submit", "task:work", "task:cancel", "task:approve", "read_file", "record_artifact"})


@pytest.fixture
def service(tmp_path):
    authenticator = Authenticator({"a": ("alice", PERMISSIONS), "b": ("bob", PERMISSIONS),
                                  "outsider": ("eve", PERMISSIONS)})
    alice, bob, eve = [authenticator.authenticate(token) for token in ("a", "b", "outsider")]
    now = [100.0]
    server = TeamBoundary(tmp_path / "team.sqlite", authenticator, lambda: now[0],
                          memberships=[("alice", "blue"), ("bob", "blue")], projects=[("toy", "blue")],
                          known_secrets=["SECRET_FIXTURE"], artifact_scopes={"fixture/evidence": "blue"})
    yield server, authenticator, alice, bob, eve, now
    server.close()


def envelope(user="alice", **changes):
    message = TaskEnvelope(1, "task", "correlation-1", user, "blue", frozenset({"read_file"}),
                           ("fixture/evidence",), 200.0, 5, "event-1", 0)
    return replace(message, **changes)


def test_identity_must_be_minted_by_configured_authenticator(service):
    server, authenticator, alice, bob, eve, now = service
    for forged in (AuthContext("alice", PERMISSIONS), replace(bob, user_id="alice"),
                   Authenticator({"fake": ("alice", PERMISSIONS)}).authenticate("fake")):
        with pytest.raises(TeamError):
            server.read_memory(forged)
    authenticator.revoke("a")
    with pytest.raises(TeamError):
        server.read_memory(alice)


def test_private_selected_publication_consent_provenance_conflict_and_delete(service):
    server, _, alice, bob, eve, now = service
    private = server.put_memory(alice, "private", "personal preference", "alice", 20)
    original = server.put_memory(alice, "style", "four spaces", "toy/readme", 20)
    assert server.read_memory(bob) == []
    with pytest.raises(TeamError):
        server.inspect_memory(bob, private["id"])
    with pytest.raises(TeamError):
        server.publish_memory(alice, original["id"], "blue")
    shared = server.publish_memory(alice, original["id"], "blue", consent=True)
    assert [r["key"] for r in server.search_memory(bob, "spaces", scope="team", team_id="blue")] == ["style"]
    updated = server.put_memory(bob, "style", "two spaces", "bob correction", 10,
                                scope="team", team_id="blue", consent=True, expected_version=1)
    assert updated["version"] == 2
    history = server.inspect_memory(alice, shared["id"])["history"]
    assert [row["actor"] for row in history] == ["alice", "bob"]
    with pytest.raises(TeamError):
        server.put_memory(alice, "style", "stale", "alice", 10, scope="team", team_id="blue", consent=True, expected_version=1)
    with pytest.raises(TeamError):
        server.delete_memory(bob, shared["id"])
    revision = server.memory_revision(bob, scope="team", team_id="blue")
    server.delete_memory(alice, original["id"])
    assert server.read_memory(bob, scope="team", team_id="blue") == []
    assert server.memory_revision(bob, scope="team", team_id="blue") > revision
    with pytest.raises(TeamError):
        server.inspect_memory(bob, shared["id"])
    assert server.read_memory(alice)[0]["id"] == private["id"]


def test_team_project_and_task_acl_apply_before_retrieval(service):
    server, _, alice, bob, eve, now = service
    server.put_memory(alice, "project", "toy convention", "alice", 20, scope="project", project_id="toy", consent=True)
    task_id = server.submit_task(alice, "blue", "task", {}, {"read_file"})
    server.put_memory(alice, "evidence", "task observation", "fixture", 20, scope="task", task_id=task_id, consent=True)
    assert server.read_memory(bob, scope="project", project_id="toy")
    assert server.read_memory(bob, scope="task", task_id=task_id)
    for options in ({"scope": "team", "team_id": "blue"}, {"scope": "project", "project_id": "toy"},
                    {"scope": "task", "task_id": task_id}):
        with pytest.raises(TeamError):
            server.read_memory(eve, **options)
        with pytest.raises(TeamError):
            server.search_memory(eve, "", **options)
    server.set_membership("bob", "blue", False)
    with pytest.raises(TeamError):
        server.memory_revision(bob, scope="project", project_id="toy")


def test_revoked_membership_persists_across_reopen_and_owner_can_revoke_copy(service, tmp_path):
    server, authenticator, alice, bob, eve, now = service
    original = server.put_memory(alice, "fact", "fixture", "alice", 20)
    shared = server.publish_memory(alice, original["id"], "blue", consent=True)
    server.set_membership("bob", "blue", False)
    server.set_membership("alice", "blue", False)
    server.revoke_publication(alice, shared["id"])  # Owner erasure survives membership loss.
    reopened = TeamBoundary(tmp_path / "team.sqlite", authenticator, lambda: now[0],
                            memberships=[("alice", "blue"), ("bob", "blue")])
    try:
        with pytest.raises(TeamError):
            reopened.read_memory(bob, scope="team", team_id="blue")
        assert reopened.read_memory(alice)[0]["id"] == original["id"]
    finally:
        reopened.close()


def test_retention_excludes_secrets_and_erases_published_history(service):
    server, _, alice, bob, eve, now = service
    with pytest.raises(TeamError):
        server.put_memory(alice, "secret", "SECRET_FIXTURE", "fixture", 20)
    original = server.put_memory(alice, "fact", "temporary", "fixture", 5)
    shared = server.publish_memory(alice, original["id"], "blue", consent=True)
    now[0] += 6
    assert server.read_memory(bob, scope="team", team_id="blue") == []
    with pytest.raises(TeamError):
        server.inspect_memory(bob, shared["id"])
    server.prune_memory()
    assert server.db.execute("SELECT COUNT(*) FROM team_memory_history").fetchone()[0] == 0


def test_other_user_correction_cannot_extend_owner_retention(service):
    server, _, alice, bob, eve, now = service
    shared = server.put_memory(alice, "shared", "owner fact", "alice", 5, scope="team", team_id="blue", consent=True)
    server.put_memory(bob, "shared", "bob correction", "bob", 100, scope="team", team_id="blue", consent=True, expected_version=1)
    assert server.inspect_memory(alice, shared["id"])["expires"] == 105
    now[0] = 106
    assert server.read_memory(bob, scope="team", team_id="blue") == []


def test_collaboration_fanout_bound_and_outsider_cannot_claim(service):
    server, _, alice, bob, eve, now = service
    first = server.receive_task(alice, envelope(), {})
    server.receive_task(alice, envelope(idempotency_key="second"), {})
    with pytest.raises(TeamError):
        server.receive_task(alice, envelope(idempotency_key="third"), {})
    with pytest.raises(TeamError):
        server.claim_task(eve, first, worker_permissions={"read_file"})
    assert server.inspect_task(alice, first)["status"] == "queued"


def test_envelopes_auth_correlation_artifacts_version_and_order(service):
    server, _, alice, bob, eve, now = service
    for invalid in (envelope(principal="bob"), envelope(version=2), envelope(sequence=1), envelope(scope=None), envelope(scope=""),
                    envelope(artifacts=("outside/artifact",)), envelope(capabilities=frozenset({"shell"})),
                    envelope(deadline=99)):
        with pytest.raises(TeamError):
            server.receive_task(alice, invalid, {})
    task_id = server.receive_task(alice, envelope(), {"goal": "inspect"})
    assert server.receive_task(alice, envelope(), {"goal": "inspect"}) == task_id
    with pytest.raises(TeamError):
        server.receive_task(alice, envelope(), {"goal": "changed"})
    claimed = server.claim_task(alice, task_id, worker_permissions={"read_file", "shell"})
    assert claimed["permissions"] == ["read_file"]
    result = envelope(kind="result", sequence=2, remaining_budget=4)
    with pytest.raises(TeamError):
        server.receive_result(alice, task_id, claimed["fence"], result, {})
    assert server.inspect_task(alice, task_id)["status"] == "running"


@pytest.mark.parametrize("scope", [None, "", 42, "x" * 257])
def test_task_requires_explicit_valid_team_scope(service, scope):
    server, _, alice, bob, eve, now = service
    with pytest.raises(TeamError):
        server.submit_task(alice, scope, "key", {}, {"read_file"})


def test_handover_cannot_widen_authority_and_stale_peer_cannot_publish(service):
    server, _, alice, bob, eve, now = service
    task_id = server.receive_task(alice, envelope(), {})
    first = server.claim_task(alice, task_id, worker_permissions={"read_file"})
    handover = envelope(kind="handover", sequence=1, remaining_budget=4)
    for invalid in (replace(handover, capabilities=frozenset({"read_file", "record_artifact"})),
                    replace(handover, remaining_budget=5), replace(handover, deadline=201)):
        with pytest.raises(TeamError):
            server.receive_result(alice, task_id, first["fence"], invalid, {})
    server.receive_result(alice, task_id, first["fence"], handover, {"uncertainty": "fixture only"})
    with pytest.raises(TeamError):
        server.execute_peer(alice, task_id, first["fence"], provider_name="fake")
    second = server.claim_task(bob, task_id, worker_permissions={"read_file"})
    assert second["fence"] > first["fence"]
    run = server.execute_peer(bob, task_id, second["fence"], provider_name="fake-sre", domain="sre")
    assert run["stop_reason"] == "final"
    result = envelope("bob", kind="result", sequence=2, remaining_budget=run["remaining_budget"])
    server.receive_result(bob, task_id, second["fence"], result, {"observed": "synthetic health"})
    assert server.receive_result(bob, task_id, second["fence"], result, {"observed": "synthetic health"})["duplicate"]
    assert [r["sequence"] for r in server.messages(bob, task_id)] == [0, 1, 2]
    with pytest.raises(TeamError):
        server.receive_result(bob, task_id, second["fence"], result, {"observed": "changed receipt"})


def test_peer_engine_requires_exact_local_approval_and_rechecks_membership(service):
    server, _, alice, bob, eve, now = service
    task_id = server.receive_task(alice, envelope(capabilities=frozenset({"record_artifact"})), {})
    lease = server.claim_task(bob, task_id, worker_permissions={"record_artifact"})
    run = server.execute_peer(bob, task_id, lease["fence"], provider_name="fake-automation",
                              domain="automation", operation="record_artifact")
    assert run["stop_reason"] == "approval_required"
    assert server.db.execute("SELECT COUNT(*) FROM team_peer_artifacts").fetchone()[0] == 0
    approved = server.execute_peer(bob, task_id, lease["fence"], provider_name="fake-automation",
                                   domain="automation", operation="record_artifact", approval_context=alice)
    assert approved["stop_reason"] == "final"
    assert server.db.execute("SELECT COUNT(*) FROM team_peer_artifacts WHERE team_id='blue'").fetchone()[0] == 1
    server.set_membership("bob", "blue", False)
    with pytest.raises(TeamError):
        server.execute_peer(bob, task_id, lease["fence"], provider_name="fake")


def test_local_reviewer_cannot_amplify_delegated_read_authority(service):
    server, _, alice, bob, eve, now = service
    task_id = server.receive_task(alice, envelope(), {})
    lease = server.claim_task(bob, task_id, worker_permissions={"read_file", "record_artifact"})
    run = server.execute_peer(bob, task_id, lease["fence"], provider_name="fake-automation", domain="automation",
                              operation="record_artifact", approval_context=alice)
    assert run["stop_reason"] == "denied"
    assert server.db.execute("SELECT COUNT(*) FROM team_peer_artifacts").fetchone()[0] == 0


def test_crash_cancel_deadletter_and_global_budget_survive_recovery(service):
    server, _, alice, bob, eve, now = service
    task_id = server.receive_task(alice, envelope(remaining_budget=1), {})
    lease = server.claim_task(alice, task_id, worker_permissions={"read_file"}, lease_seconds=5)
    now[0] += 6
    assert server.recover_tasks() == [task_id]
    with pytest.raises(TeamError):
        server.complete_task(alice, task_id, lease["fence"], {})
    with pytest.raises(TeamError):
        server.claim_task(bob, task_id, worker_permissions={"read_file"})
    with pytest.raises(TeamError):
        server.reconcile_task(bob, task_id, observed=False, effect_completed=False)
    server.reconcile_task(bob, task_id, observed=True, effect_completed=False)
    assert server.inspect_task(bob, task_id)["status"] == "dead_letter"
    cancelled = server.receive_task(alice, envelope(idempotency_key="event-2"), {})
    server.cancel_task(alice, cancelled)
    with pytest.raises(TeamError):
        server.claim_task(bob, cancelled, worker_permissions={"read_file"})
    assert server.inspect_task(bob, cancelled)["status"] == "cancelled"
    server.db.execute("UPDATE team_controls SET value=0 WHERE key='budget'")  # Host fixture exhaustion.
    queued = server.receive_task(alice, envelope(idempotency_key="event-3", correlation_id="other"), {})
    with pytest.raises(TeamError):
        server.claim_task(alice, queued, worker_permissions={"read_file"})


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_lesson_31_checkpoint(scenario):
    result = checkpoint(31, scenario)
    assert result["status"] == "passed"
    assert result["checks"]["private_before_publish"] and result["checks"]["revoked_cache_authorization"]


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_lesson_32_checkpoint(scenario):
    result = checkpoint(32, scenario)
    assert result["status"] == "passed"
    assert all(result["checks"][name] for name in ("coding_harness_ran", "sre_harness_ran", "automation_harness_ran"))
    assert result["checks"]["cancel_fences_worker"] and result["checks"]["global_budget"]
