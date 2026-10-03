"""Optional boundaries and an entirely offline GitHub mention replay.

No framework is imported by the core. No GitHub API, webhook, Actions workflow,
credential, subprocess or deployment is activated by these examples.
"""
from dataclasses import dataclass
import hashlib
import hmac
import json
import re
import time

from .core import Engine, Limits
from .providers import FakeProvider, Reply, ToolCall, ProviderError
from .tools import Policy, FixtureWorld, scenario_tools, canonical
from .resident import ResidentQueue


class FrameworkProvider:
    """A suggestion callback, not a second tool or session owner.

    The callback is trusted/cooperative. Check before AND after it returns;
    noncooperative framework code requires process isolation outside this example.
    """
    def __init__(self, callback, *, max_calls=3, cancelled=lambda: False, clock=time.monotonic, seconds=5):
        if max_calls < 1 or seconds <= 0:
            raise ValueError("invalid framework bounds")
        self.callback, self.remaining = callback, max_calls
        self.cancelled, self.clock, self.seconds = cancelled, clock, seconds

    def complete(self, messages, tools=()):
        if self.cancelled():
            raise InterruptedError("framework cancelled")
        if self.remaining <= 0:
            raise ProviderError("framework_budget")
        self.remaining -= 1
        start = self.clock()
        reply = self.callback(messages, tools)
        if self.cancelled():
            raise InterruptedError("framework cancelled")
        if self.clock() - start >= self.seconds:
            raise TimeoutError("framework deadline")
        # Reuse the fake provider's complete reply contract, including JSON limits.
        return FakeProvider([reply]).complete(messages, tools)


class FrameworkToolBridge:
    """Expose a host-owned operation to a framework through the same controller."""
    def __init__(self, registry, policy, *, state_store=None, max_calls=3, cancelled=lambda: False):
        if max_calls < 1:
            raise ValueError("invalid bridge budget")
        self.registry, self.policy, self.state_store = registry, policy, state_store
        self.remaining, self.cancelled, self.sequence = max_calls, cancelled, 0

    def invoke(self, name, arguments):
        if self.cancelled():
            raise InterruptedError("bridge cancelled")
        if self.remaining <= 0:
            raise PermissionError("bridge global call budget exhausted")
        self.remaining -= 1
        self.sequence += 1
        script = FakeProvider([Reply(calls=(ToolCall(f"framework-{self.sequence}", name, arguments),)), Reply("operation observed")])
        return Engine(script, self.registry, self.policy, limits=Limits(steps=2, calls=1), cancelled=self.cancelled, state_store=self.state_store).run("Framework requests a host operation; framework prose grants no authority.")


class FakeGitHub:
    """Course-owned fake API. All identities and check receipts are synthetic.

    A real adapter must authenticate with GitHub and recheck current permissions;
    this dictionary is not GitHub authentication or a secure hosted service.
    """
    def __init__(self):
        self.head = "a" * 40
        self.repo = "classroom/toy"
        self.permissions = {"alice": "write", "bob": "read"}
        self.comments = {1: {"actor": "alice", "body": "@course-harness fix", "revision": 1, "deleted": False, "bot": False}}
        self.branches, self.prs = {}, {}
        self.trace = []
        self.ambiguous_publish = False
        self.rate_limited = False

    def comment(self, comment_id):
        value = self.comments.get(comment_id)
        if value is None or value["deleted"]:
            raise PermissionError("comment is absent/deleted")
        return dict(value)

    def permitted(self, actor):
        return self.permissions.get(actor) in {"write", "maintain", "admin"}

    def prepare(self, key, *, base):
        if base != self.head:
            raise ValueError("stale base")
        # Exact toy branch using the SAME controller. Host policy grants a
        # narrow disposable edit; comment text never supplies that authority.
        world = FixtureWorld()
        registry = scenario_tools(world)
        before = world.files["calculator.py"]
        after = "def add(a, b):\n    return a + b\n"
        script = [Reply(calls=(ToolCall("read", "read_file", {"path": "calculator.py"}),)), Reply(calls=(ToolCall("patch", "patch_file", {"path": "calculator.py", "expected": before, "replacement": after}),)), Reply(calls=(ToolCall("verify", "read_file", {"path": "calculator.py"}),)), Reply("fixture patch verified")]
        policy = Policy("autonomous", frozenset({"read_file", "patch_file"}), run_id=key)
        result = Engine(FakeProvider(script), registry, policy).run("Fix only the classroom calculator in its disposable branch.")
        import difflib
        diff = "".join(difflib.unified_diff(before.splitlines(True), world.files["calculator.py"].splitlines(True), fromfile="calculator.py", tofile="calculator.py"))
        # Pure fixture checks inspect the proposed state; they do not execute
        # checked-out/untrusted Python. A live adapter needs a separately approved
        # isolated checker and recorded exit status, never this synthetic receipt.
        branch = {"base": base, "path": "calculator.py", "before": before, "after": world.files["calculator.py"], "diff": diff, "checks": {"synthetic_expected_state": world.files["calculator.py"] == after and result.stop_reason == "final", "only_allowlisted_path": set(world.originals) == {"calculator.py"}}, "engine_trace": result.trace}
        self.branches.setdefault(key, branch)
        self.trace.append({"event": "isolated_fake_branch", "key": key})
        return self.branches[key]

    def find_pr(self, key):
        return self.prs.get(key)

    def draft_pr(self, key, *, expected_base):
        if self.rate_limited:
            raise ProviderError("rate_limit", retryable=True)
        if expected_base != self.head:
            raise ValueError("stale base at publish")
        if key in self.prs:
            return self.prs[key]
        result = {"number": len(self.prs) + 1, "draft": True, "key": key, "merged": False, "fake_url": f"fixture://pull/{len(self.prs) + 1}"}
        self.prs[key] = result
        if self.ambiguous_publish:
            raise TimeoutError("synthetic lost publication acknowledgement")
        return result


class MentionReceiver:
    """Signature -> fresh API authorization -> parser -> bounded durable queue.

    Single local consumer classroom model. Signature verification demonstrates a
    trust mechanism with a synthetic secret; it does not configure a live webhook.
    """
    def __init__(self, store, client, *, secret: bytes, repositories=frozenset({"classroom/toy"}), per_user=2, capacity=8):
        if not secret or per_user < 1:
            raise ValueError("invalid receiver configuration")
        self.store, self.client, self.secret = store, client, secret
        self.repositories, self.per_user = repositories, per_user
        self.queue = ResidentQueue(store, capacity=capacity)

    def sign(self, body):
        """Fixture sender only. Never expose a signing method on a real receiver."""
        return "sha256=" + hmac.new(self.secret, body, hashlib.sha256).hexdigest()

    def receive(self, body: bytes, signature: str):
        if len(body) > 8192 or not isinstance(signature, str) or not hmac.compare_digest(self.sign(body), signature):
            raise PermissionError("webhook signature rejected")
        event = json.loads(body)
        if set(event) != {"repository", "comment_id", "revision", "base", "fork", "action"}:
            raise ValueError("event contract")
        if event["repository"] not in self.repositories or event["repository"] != self.client.repo or event["fork"] is not False:
            raise PermissionError("repository/fork not trusted")
        key = f"{event['repository']}:{event['comment_id']}"
        existing = [t for t in self.queue.inspect() if t["dedup_key"] == key]
        if event["action"] == "deleted":
            # An authenticated repository deletion event can only invalidate
            # existing work. It creates no authority and needs no vanished body.
            for task in existing:
                self.queue.cancel(task["id"])
            return {"status": "invalidated", "key": key}
        comment = self.client.comment(event["comment_id"])
        actor = comment["actor"]  # Fresh fake API record, never event JSON identity.
        if comment["bot"] or not self.client.permitted(actor):
            raise PermissionError("actor lacks current repository permission")
        if event["action"] == "edited":
            for task in existing:
                self.queue.cancel(task["id"])
            return {"status": "invalidated", "key": key}
        if event["action"] != "created" or event["revision"] != comment["revision"] or event["base"] != self.client.head:
            raise ValueError("stale event/base")
        line = comment["body"].splitlines()[0]
        match = re.fullmatch(r"@course-harness (plan|fix|cancel)(?: ([0-9]+))?", line)
        if match is None or len(comment["body"]) > 4096:
            raise ValueError("exact mention/command required")
        command, target = match.groups()
        if command == "cancel":
            if target is None:
                raise ValueError("cancel requires task ID")
            task = self.queue.task(int(target))
            if task["payload"]["actor"] != actor or task["payload"]["repo"] != event["repository"]:
                raise PermissionError("cannot cancel another principal's task")
            self.queue.cancel(task["id"])
            return {"status": "cancelled", "task_id": task["id"]}
        if target is not None:
            raise ValueError("plan/fix take no shell or argv arguments")
        if existing:
            return {"status": "duplicate", "task_id": existing[0]["id"]}
        active = [t for t in self.queue.inspect() if t["status"] in self.queue.ACTIVE and t["payload"].get("actor") == actor]
        if len(active) >= self.per_user:
            raise PermissionError("per-user admission budget")
        payload = {"actor": actor, "repo": event["repository"], "comment_id": event["comment_id"], "revision": comment["revision"], "command": command, "base": event["base"], "text": comment["body"]}
        task_id = self.queue.enqueue(key, payload)
        return {"status": "admitted", "task_id": task_id}

    def publication_digest(self, task, branch):
        return hashlib.sha256(canonical({"task": task["id"], "actor": task["payload"]["actor"], "base": branch["base"], "diff": branch["diff"], "checks": branch["checks"]}).encode()).hexdigest()

    def prepare_next(self):
        task = self.queue.claim("mention-worker")
        if task is None:
            return None
        payload = task["payload"]
        try:
            comment = self.client.comment(payload["comment_id"])
            if (not self.client.permitted(payload["actor"]) or comment["actor"] != payload["actor"] or comment["revision"] != payload["revision"] or comment["bot"] or task["cancelled"]):
                raise PermissionError("permission/comment changed")
            branch = self.client.prepare(task["dedup_key"], base=payload["base"])
        except (PermissionError, ValueError):
            self.queue.reject(task["id"], "mention-worker", reason="current authorization or precondition failed")
            raise
        except Exception:
            self.queue.fail(task["id"], "mention-worker", safe_to_retry=False)
            raise
        return {"task": task, "branch": branch, "digest": self.publication_digest(task, branch), "trace": [{"event": "authenticated_event"}, {"event": "task_claimed"}] + branch["engine_trace"] + [{"event": "fake_branch_diff"}, {"event": "synthetic_check_receipt"}, {"event": "publication_approval_required"}]}

    def publish(self, task_id, *, approval_digest, approval_expires):
        """Trusted operator API, never a model tool or webhook JSON action.

        Production needs authenticated operator identity and durable consent;
        the local fixture tests call this boundary directly as the operator.
        """
        task = self.queue.task(task_id)
        self.queue._owned(task_id, "mention-worker")
        payload = task["payload"]
        if task["cancelled"] or self.store.control("human_stop", False):
            raise PermissionError("cancelled/stopped")
        current = self.client.comment(payload["comment_id"])
        if not self.client.permitted(payload["actor"]) or current["revision"] != payload["revision"] or current["actor"] != payload["actor"]:
            raise PermissionError("current permission/comment rejected")
        branch = self.client.branches[task["dedup_key"]]
        if payload["command"] != "fix" or not all(branch["checks"].values()) or approval_expires <= self.store.clock() or approval_digest != self.publication_digest(task, branch):
            raise PermissionError("exact fresh approval/checks required")
        try:
            receipt = self.client.draft_pr(task["dedup_key"], expected_base=payload["base"])
        except ProviderError:
            self.queue.fail(task_id, "mention-worker", safe_to_retry=True)
            raise
        except Exception:
            self.queue.fail(task_id, "mention-worker", safe_to_retry=False)
            raise
        self.queue.complete(task_id, "mention-worker", receipt)
        return receipt

    def reconcile_publication(self, task_id):
        task = self.queue.task(task_id)
        receipt = self.client.find_pr(task["dedup_key"])
        if receipt is None:
            raise PermissionError("effect still uncertain; human resolution required")
        self.queue.reconcile(task_id, receipt, observed=True)
        return receipt


def checkpoint(lesson, scenario):
    if lesson == 29:
        world = FixtureWorld()
        registry = scenario_tools(world)
        policy = Policy(allowed=frozenset({"observe_health", "read_file"}))
        bridge = FrameworkToolBridge(registry, policy, max_calls=2)
        observed = bridge.invoke("observe_health", {})
        denied = bridge.invoke("restart_service", {"service": "toy-service"})
        adapter = FrameworkProvider(lambda messages, tools: Reply("offline framework-shaped suggestion"), max_calls=1)
        adapter.complete([{"role": "user", "content": scenario}])
        try:
            adapter.complete([])
        except ProviderError:
            bounded = True
        else:
            bounded = False
        return {"checks": {"read_observed": observed.stop_reason == "final", "nested_denied": denied.stop_reason == "denied" and world.restarts == 0, "framework_budget": bounded}, "trace": observed.trace + denied.trace}
    if lesson != 30:
        raise ValueError("extension checkpoint must be 29 or 30")
    from .persistence import DurableStore
    store = DurableStore(":memory:", clock=lambda: 100.0)
    try:
        client = FakeGitHub()
        receiver = MentionReceiver(store, client, secret=b"synthetic-webhook-key")
        event = {"repository": client.repo, "comment_id": 1, "revision": 1, "base": client.head, "fork": False, "action": "created"}
        raw = canonical(event).encode()
        first = receiver.receive(raw, receiver.sign(raw))
        duplicate = receiver.receive(raw, receiver.sign(raw))
        prepared = receiver.prepare_next()
        receipt = receiver.publish(first["task_id"], approval_digest=prepared["digest"], approval_expires=101)
        replay = receiver.receive(raw, receiver.sign(raw))
        return {"checks": {"duplicate_suppressed": duplicate["task_id"] == first["task_id"], "one_draft": len(client.prs) == 1 and receipt["draft"] and not receipt["merged"], "replay_receipt": replay["status"] == "duplicate", "bounded_fixture_diff": prepared["branch"]["after"] == "def add(a, b):\n    return a + b\n"}, "trace": prepared["trace"] + [{"event": "fake_draft_pr", "number": receipt["number"]}]}
    finally:
        store.close()
