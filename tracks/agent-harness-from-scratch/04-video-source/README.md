# Narration and transcript source

These files are readable teaching scripts, not evidence that recordings exist.
They follow the same incremental labs and describe diagrams and successful/failing
paths in words. Advanced scripts explicitly identify fixture-only mechanisms and
unsupported runtime behavior. Use the lab text and separate solutions during pauses.

- [00: Foundations without hidden prerequisites](00-foundations.md)
- [01: Models, agents, harnesses and fake responses](01-models-and-harnesses.md)
- [02: CLI conversations and visible state](02-cli-conversations.md)
- [03: Shared LLM helpers and an optional API call](03-shared-llm-helpers.md)
- [04: Tool contracts and dispatch](04-tool-contracts.md)
- [05: The bounded agent loop](05-bounded-agent-loop.md)
- [06: Trust boundaries, permissions and approvals](06-permissions-and-approvals.md)
- [07: Coding tools in a disposable workspace](07-coding-workspace.md)
- [08: Read-only SRE evidence](08-sre-observations.md)
- [09: Automation plans and bounded autonomy](09-automation-modes.md)
- [10: Restricted commands and toy remediation](10-restricted-commands.md)
- [11: Bounded context and outputs](11-context-and-output-bounds.md)
- [12: Retries, deadlines and cancellation](12-retries-and-cancellation.md)
- [13: Durable state and reconciliation](13-durable-state.md)
- [14: Resident queue and lifecycle](14-resident-lifecycle.md)
- [15: Explicit memory and retention](15-explicit-memory.md)
- [16: Five provider adapters, one honest contract](16-five-providers.md)
- [17: Streaming without partial tool execution](17-stream-assembly.md)
- [18: Model switching and constrained handover](18-handover.md)
- [19: Configuration, skills and trusted plugins](19-configuration-and-extensions.md)
- [20: Traces, usage and resident health](20-traces-and-health.md)
- [21: Tests organized by boundary](21-testing-strategy.md)
- [22: Task outcomes and regression evidence](22-task-evaluations.md)
- [23: Stress, injection and failure testing](23-failure-injection.md)
- [24: Two workers and one global budget](24-bounded-workers.md)
- [25: Efficiency without weakening gates](25-measured-efficiency.md)
- [26: Resident operations and graceful degradation](26-resident-operations.md)
- [27: Controlled improvement and rollback](27-improvement-and-rollback.md)
- [28: Read public source and justify one small change](28-source-study.md)
- [29: Integrate a framework after learning the internals](29-framework-bridge.md)
- [30: A GitHub mention becomes bounded draft work](30-github-mentions.md)
- [31: Multiple users and central memory](31-shared-memory.md)
- [32: Collaboration between separate harnesses](32-harness-collaboration.md)

Recording checklist: first validate the lesson's source, then capture real command
output; caption spoken explanations; describe every meaningful visual state;
retain failure reasoning and learner pauses; preserve the fake-provider default.
No recording should suggest that synthetic SRE fixtures are production incidents
or that a classroom policy gate supplies OS isolation.
