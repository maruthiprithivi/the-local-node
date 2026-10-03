# Plain-language glossary

| Term | Meaning in this course |
| --- | --- |
| Model | A program that predicts a response from supplied input. Its confidence is not authority. |
| Provider | The boundary that obtains a model response, including the scripted fake provider. |
| Agent | A goal-directed model/tool interaction whose actions remain controlled by ordinary code. |
| Harness | The surrounding controller, tools, policy, state, limits, and evidence that make runs inspectable. |
| Tool | A named operation with validated arguments and a structured result. A description is not enforcement. |
| Contract | The accepted input, output, and error shapes at a boundary. |
| Adapter | Code translating one provider's actual protocol to the shared contract. |
| Turn | One model request and response. A turn may request tools. |
| Run | One bounded attempt to handle a task, ending with a recorded stop reason. |
| Session | Ordered conversation history that can contain several runs. |
| Context | The bounded messages and observations selected for one model call. |
| Token | A model's unit of text representation. Character-based estimates are approximate. |
| Fixture | A controlled input, such as fake replies, toy files, or synthetic metrics. |
| Deterministic | Repeating the same controlled inputs produces the same meaningful result. |
| Policy | Host-owned rules deciding allow, deny, or ask before execution. |
| Approval | Permission bound to a specific action and arguments, target, and scope. |
| Autonomy | Execution within explicit allowlists and budgets; it does not mean unlimited authority. |
| Semi-autonomy | The run pauses for a required human decision while retaining pending state. |
| Trust label | Metadata describing the origin/authority of information; it does not make data safe automatically. |
| Injection | Untrusted text attempting to become an instruction or change permissions. |
| Isolation | A boundary enforced outside the application, such as a separately scoped OS process/container. |
| Budget | A ceiling on work: calls, actions, steps, output, or time. |
| Deadline | The last permitted time for a run, distinct from a timeout on one operation. |
| Idempotent | Repeating an operation with the same identity has the same defined effect as once. |
| Reconciliation | Inspecting actual state to resolve an action whose effect is uncertain. |
| Durable | Persisted state survives process exit; this does not promise every storage device failure is recoverable. |
| Queue | Stored tasks awaiting admission/claim/execution. |
| Lease | Temporary ownership of queued work; expiration does not prove an effect never happened. |
| Backpressure | A defined response when more work arrives than the bounded system can admit. |
| Dead letter | Inspectable work no longer eligible for automatic retries. |
| Human stop | Persisted operator intent to prevent new execution, including after restart. |
| Trace | Ordered evidence of controller decisions, calls, results, and stop reasons. |
| Evaluation | Measurement of task outcomes; a passing unit test is not proof a diagnosis is correct. |
| Handover | A bounded packet of goal, evidence, effects, pending work, uncertainty, and remaining limits. |
| Capability | An adapter's explicitly supported behavior, such as complete tool calls or streaming. |
| Resident service | A process that waits for events over time, with ordinary queue and lifecycle code. |

When explaining a trace, use concrete words first: “the controller denied the write before the executor ran.” Only then shorten this to “policy enforcement.”

