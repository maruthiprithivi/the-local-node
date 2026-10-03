# An inspectable harness

An agent is a loop with a goal and tools. The harness owns the loop around a model;
the resident supervisor owns ordinary service behavior around runs. Neither
scheduling nor permission enforcement belongs in a model prompt.

```text
CLI / fixture event / schedule
             |
     admission + durable queue
             |
    controller + shared budgets <--- cancellation / human stop
             |
   context builder + trust labels <--- explicit memory
             |
   shared provider request/response
       fake / OpenAI / Gemini / DeepSeek / Ollama / NVIDIA
             |
    validated tool request
             |
       host policy + exact approval
             |
      authorized executor
       coding / SRE / automation
             |
     tool result --> next turn or stop

Persistence, trace events and evaluations observe these transitions.
```

Text equivalent: an interface admits bounded work to a durable queue. A controller
loads the goal and remaining budgets, builds bounded context, and asks a provider.
A provider returns text or structured action proposals. The tool layer validates
the proposal; host policy allows, denies, or requires exact approval. Only an
authorized executor performs an operation. A result goes back to the controller,
which continues or stops. Cancellation can interrupt admission and execution.
Memory supplies evidence; it never supplies permission.

The package stays small. `core.py` holds the request loop and controller limits;
`providers.py` holds API normalization; `tools.py` holds domain operations and
argument validation; `persistence.py` holds durable state; `resident.py` holds
queue and lifecycle behavior; `advanced.py` holds later inspectable mechanisms.
The CLI connects these components and prints evidence. This is a teaching layout,
not a claim that one file per topic is a production architecture.

Later `streaming.py` decodes native offline byte fixtures before full-call
validation, and `observability.py` provides bounded/redacted correlated records.
The separate extensions use `extensions.py` for optional callback/tool bridges
and offline mention replay, and `team.py` for a simulated authenticated service
boundary, scoped shared memory and fenced task envelopes. Core installation still
does not import an orchestration framework. Live stream transport, real identity
verification and multi-host service deployment are separate from fixture evidence.

Introduce a boundary only after experiencing the problem it solves. First a fake
reply makes state visible. A second tool makes dispatch useful. A denied mutation
makes policy necessary. A crash after an effect makes durable uncertain state
necessary. Repeated events make admission and deduplication necessary. Later,
provider variation, streams, memory, handovers and workers reuse these boundaries.

| Component | Owns | Must not own |
|---|---|---|
| Provider | Request encoding, response decoding, capability declarations | Tool execution or permission decisions |
| Controller | Steps, calls, stop reasons, result correlation | Unbounded retries or silent provider changes |
| Policy | Host allowlists and exact approval binding | Model-generated permission changes |
| Executor | One already-authorized bounded operation | Interpreting arbitrary generated code |
| Store | Versioned records and recovery evidence | Assuming timeout proves no effect |
| Resident supervisor | Admission, leases, lifecycle and stop | Prompt-based scheduling or clearing human stop |
| Memory | Scoped evidence with provenance and retention | Overriding host policy |
| Coordinator | Worker scopes, shared budgets and conflict visibility | Recursive uncontrolled spawning |

Three paths share the controller. Coding reads a toy file, proposes a patch, waits
for approval, applies it and verifies the result. SRE reads synthetic observations,
separates facts from hypotheses, and later restarts only the named toy service
under a bounded policy. Automation consumes fixture events, plans in dry-run,
queues an approval or performs an allowlisted local action. All paths keep stable
identifiers and record uncertainty after a potentially completed effect.

An approval describes the operation, target and arguments. It is not a blanket
approval for all later model suggestions. A changed patch, target or relevant
argument needs a new decision. A completed durable result is replayed as evidence;
an uncertain action is inspected before retry. Deduplication applies within the
documented key and retention scope; it is not universal exactly-once delivery.

Context, memory, repository files, logs and worker messages are untrusted evidence.
Even correct evidence can become stale. Summaries can omit facts or invent them.
The host retains policy and budgets outside that content. Application checks,
path restrictions, approvals and tests are not OS isolation or a production
security guarantee. Stronger process/container isolation is a separately scoped
extension; see [threat model](threat-model.md) and [limitations](limitations.md).
