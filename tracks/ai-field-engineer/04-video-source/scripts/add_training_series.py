"""One-off: add videos 14–18 (training deep dives) and repoint every end card at repo lessons + lab ids."""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "src" / "narration.json"
d = json.loads(P.read_text())

def S(visual, text, **params):
    return {"visual": visual, "params": params, "text": text}

def title(n, headline, sub, learn, text, extra=""):
    return S("Title", text, kicker=f"Video {n} of 18 · training deep dive{extra}", headline=headline, sub=sub, learn=learn)

V = {}

# ───────────────────────────── 14 · Full fine-tuning ─────────────────────────────
V["full-finetuning"] = {"title": "Full Fine-Tuning", "subtitle": "Every weight moves, and what that costs", "accent": "teal", "scenes": [
    title(14, "Full fine-tuning", "Every weight moves, and what that costs",
          "what full fine-tuning is, why it needs about 16 bytes per parameter, and when it is worth it",
          "This is the first of five deep dives on training. We start with the most direct way to change a model: full fine-tuning, where every single weight is allowed to move. It is the most powerful option and the most expensive, and you should know exactly why."),
    S("TrainLoop", "Every kind of training runs the same loop. The model reads an example and predicts each next token. The loss measures how surprised it was by the right answer. Backpropagation works out, for every weight, which direction would have reduced that surprise. Then the optimizer nudges each weight a tiny step in that direction, and the loop repeats, thousands of times.",
      note="Full fine-tuning, LoRA, SFT and DPO all run this loop. They differ in which weights move and what the loss rewards."),
    S("WeightUpdate", "In full fine-tuning, that nudge applies to every weight. For a seven billion parameter model, that is seven billion numbers updated on every step. Nothing is frozen. It is like re-editing an entire encyclopedia, where LoRA would add a few sticky notes.",
      mode="full", note="A 7B model: 7,000,000,000 trainable numbers, every step."),
    S("MemoryLedger", "Here is where the cost comes from. Serving a model only needs the weights, about two bytes each. Training needs far more per parameter: the weights, a gradient of the same size, the Adam optimizer's two running averages kept in full precision, and a full precision master copy. That is roughly sixteen bytes per parameter before you count activations. For seven billion parameters, that is over a hundred gigabytes.",
      paramsB=7, totalText="112 GB + activations", note="Serving the same model needs about 14 GB. Training needs about 8× that."),
    S("Worked", "Put numbers on it. A one billion parameter model needs about sixteen gigabytes, which is one large GPU. An eight billion model needs around a hundred and thirty, so at least two eighty-gigabyte GPUs. A seventy billion model needs over a terabyte, which means sixteen H100s and a sharding framework like DeepSpeed ZeRO or FSDP to split the weights, gradients and optimizer state across them. LoRA on that same seventy billion model needs a small fraction of that.",
      heading="Worked example · what full fine-tuning needs", scenario="≈16 bytes per parameter, plus activations",
      rows=[["1B model", "≈ 16 GB · one big GPU"], ["8B model", "≈ 130 GB · 2× H100 80 GB"], ["70B model", "≈ 1.1 TB · 16× H100 + sharding"], ["LoRA on the same 70B", "≈ 160 GB · 2–4× H100"]],
      answer="Memory, not compute, decides whether you can full fine-tune"),
    S("CardGrid", "Teams make it fit with a standard toolbox. Mixed precision computes in bf16. ZeRO or FSDP shards everything across GPUs. Gradient checkpointing recomputes activations instead of storing them, trading time for memory. Eight-bit optimizers shrink the Adam state. Offloading parks state in system memory, at a speed cost. And often the best move is a smaller model.",
      heading="How teams make full fine-tuning fit", cols=3,
      cards=[["Mixed precision", "bf16 compute, fp32 master copy", "≈16 B/param"], ["ZeRO / FSDP", "shard weights, grads, optimizer across GPUs", "memory ÷ N GPUs"], ["Grad checkpointing", "recompute activations, don't store them", "less memory, ~30% slower"],
             ["8-bit optimizers", "Adam state in 8 bits", "16 → ≈10 B/param"], ["CPU offload", "optimizer state in system RAM", "fits more, runs slower"], ["Right-size the model", "a full 8B tune can beat a 70B LoRA", "try this first"]]),
    S("BeforeAfter", "Compare it with LoRA on the same eight billion model and the same data. Full fine-tuning trains eight billion parameters in around a hundred and thirty gigabytes. LoRA trains about twenty million in about twenty. The full checkpoint is sixteen gigabytes; the adapter is about forty megabytes. On a narrow task, LoRA usually lands within a point or two. Full fine-tuning also risks more forgetting, where the model gets better at your task and worse at everything else.",
      heading="Same 8B model, same data", beforeLabel="full fine-tune", afterLabel="LoRA",
      rows=[["trainable parameters", "8 billion", "≈ 20 million"], ["training memory", "≈ 130 GB", "≈ 20 GB"], ["checkpoint", "16 GB", "≈ 40 MB"], ["narrow-task quality", "best", "within 1–2 pts"], ["forgetting risk", "higher", "lower"]],
      note="For narrow tasks, try LoRA first; go full when the gap is real and measured."),
    S("Bullets", "So when is full fine-tuning worth it? When you are moving the model a long way, like a new language or a highly specialised domain. When you have a lot of data, hundreds of thousands of examples or more. When the model will run on its own dedicated capacity anyway. And when you have evaluations that would catch the model forgetting its general skills.",
      heading="When full fine-tuning is worth it",
      items=["A big shift: new language, deep domain vocabulary, new modality", "Lots of data: hundreds of thousands of examples or more", "It will run on dedicated capacity anyway", "You have evals that would catch forgetting"]),
    S("CommandCard", "You can feel this on a laptop. Lesson seventeen trains the same small model three ways, full, LoRA and DoRA, on the ticket data, and prints peak memory, training time, checkpoint size and accuracy side by side. Watch the peak memory line for the full run.",
      heading="Run it · lesson 17 on your Mac",
      lines=["# same data, three ways: compare memory and quality", "cd lessons/17-full-vs-peft-mlx", "python peft_params.py --model 0.5b", "bash run_variants.sh        # full · lora · dora", "python compare_variants.py  # memory, time, size, accuracy"]),
    S("Recap", "Three things to take away. Full fine-tuning updates every weight: the most powerful option and the most expensive. Training needs about sixteen bytes per parameter against two for serving, so memory decides what is possible. And right-size the model and try LoRA first; go full when the shift is big and the gap is measured.",
      heading="Recap", items=["Full fine-tuning updates every weight: most power, most cost", "≈16 bytes per parameter to train vs ≈2 to serve", "Right-size and try LoRA first; go full when the gap is real"]),
    S("EndCard", "Next, supervised fine-tuning: the data format almost every customisation starts with. And when you are ready to run it: lesson seventeen, lab T2, full versus LoRA versus DoRA on your Mac.",
      line="Lesson 17 · Lab T2 — full vs LoRA vs DoRA on your Mac"),
]}

# ───────────────────────────── 15 · SFT ─────────────────────────────
V["sft"] = {"title": "Supervised Fine-Tuning", "subtitle": "Teaching by example", "accent": "copper", "scenes": [
    title(15, "Supervised fine-tuning", "Teaching by example",
          "what SFT data looks like, why only the answer is graded, and how to tell it is working",
          "Supervised fine-tuning is where almost every customisation starts. You show the model examples of exactly what you want, and it learns to imitate them. The idea is simple, and most of the skill is in the data."),
    S("TrainingPipeline", "First, where it sits. A base model is pretrained on trillions of tokens, then its creator instruction-tunes it. Supervised fine-tuning is the next step, done by you, on your task: a prompt in, the ideal answer out, thousands of times.", stage=1),
    S("LossMask", "Here is one training example for ticket triage: a system message, the customer's ticket, and the ideal JSON answer. The key detail is where the loss is counted. The system and user parts are context, so the model is not graded on predicting them. Only the assistant's answer is graded. This is called masking the prompt. Forget it, and you partly teach the model to write tickets instead of triaging them.",
      note="Check your trainer: mlx-lm needs --mask-prompt; TRL needs assistant_only_loss=True."),
    S("CommandCard", "On disk it is plain JSON lines, one conversation per line, in the same chat format the API uses. Fireworks, MLX, TRL and Unsloth all accept it, so one dataset works on every platform. Our labs rely on exactly that.",
      heading="The data format · JSONL, one example per line",
      lines=['{"messages": [', '  {"role": "system",    "content": "You triage tickets..."},', '  {"role": "user",      "content": "Card declined twice..."},', '  {"role": "assistant", "content": "{\\"category\\": \\"billing\\"}"}', "]}", "", "# Fireworks, MLX, TRL and Unsloth all read this format"]),
    S("Bullets", "Data quality decides the result. Consistent, so similar inputs get similar answers. Covering, so every category and edge case appears. Clean, because the model learns a wrong label just as confidently as a right one. And held out: split off your test set before training, and never train on it.",
      heading="Data beats everything",
      items=["Consistent: the same kind of input always gets the same kind of answer", "Covering: every category, edge case and refusal you care about", "Clean: a wrong label is learned as confidently as a right one", "Held out: split the test set off first; never train on it"]),
    S("Worked", "How much data? These are typical ranges for a task like triage, not guarantees. Fifty examples mostly fix the format. Five hundred usually buy eight to twelve points of accuracy. Two thousand get most of the way, and then the curve flattens. Twenty thousand noisy examples often do worse than two thousand clean ones. Start small and clean, then add examples exactly where the evaluation shows gaps.",
      heading="Worked example · how much data?", scenario="ticket triage · 7B base · LoRA SFT · typical ranges",
      rows=[["50 examples", "format fixed, accuracy barely moves"], ["500 examples", "+8 to 12 points"], ["2,000 examples", "+12 to 16, then flattens"], ["20,000 noisy examples", "worse than 2,000 clean"]],
      answer="A few hundred clean examples first; add more where evals show gaps", answerLabel="Rule of thumb"),
    S("Bullets", "Only a few knobs matter. Epochs, the number of passes over the data: one to three, because more usually memorises. Learning rate: around one times ten to the minus four for LoRA, about ten times smaller for full fine-tuning. A sequence length long enough for your real examples. And watch validation loss, but trust the task evaluation.",
      heading="The knobs that matter",
      items=["Epochs: 1–3 passes; more usually memorises", "Learning rate: LoRA ≈ 1e-4 · full fine-tune ≈ 1e-5", "Max length: fits your longest real example", "Watch validation loss; decide on the task eval"]),
    S("BeforeAfter", "Read the two loss curves together. If training and validation loss both fall, it is learning. If training loss keeps falling while validation loss rises, it is memorising the examples, so stop earlier or add data. If both stay flat and high, it is not learning at all: check the data format, or raise the learning rate.",
      heading="Reading the loss curves", beforeLabel="means", afterLabel="do",
      rows=[["train ↓ · validation ↓", "learning", "keep going"], ["train ↓ · validation ↑", "memorising", "stop earlier, add data"], ["both flat and high", "not learning", "check data, raise LR"]]),
    S("Worked", "Know its limits. Supervised fine-tuning is excellent at format, tone, domain style and house rules. It is poor at injecting facts that change, which is a job for retrieval. And when both candidate answers are acceptable but one is better, you need preference tuning, which is videos seventeen and eighteen.",
      heading="What SFT can and cannot do",
      rows=[["output format, JSON, tone", "✓ very good"], ["domain vocabulary and style", "✓ good"], ["house rules and refusals", "✓ good"], ["facts that change weekly", "✗ use retrieval"], ["taste between two OK answers", "✗ preference tuning"]],
      answer="SFT teaches behaviour, not knowledge"),
    S("CommandCard", "In the labs, the same training file goes through three trainers: Fireworks in lesson ten, MLX on your Mac in lesson eleven, and in lesson seventeen a data checker that catches the mistakes that ruin runs: missing assistant turns, duplicates, leaked test examples and over-long rows.",
      heading="Run it · lessons 10, 11 and 17",
      lines=["# one train.jsonl, three trainers", "python lessons/17-full-vs-peft-mlx/sft_data_check.py", "bash lessons/11-lora-local-mlx/1_train_mlx.sh   # Mac", "bash lessons/10-lora-fireworks/1_train.sh       # managed"]),
    S("Recap", "Three things to take away. Supervised fine-tuning means imitating examples, and the loss is counted on the answer only. A few hundred clean, consistent examples beat many noisy ones. And it teaches behaviour and format, not facts that change.",
      heading="Recap", items=["SFT imitates examples; loss is counted on the answer only", "A few hundred clean, consistent examples beat many noisy ones", "Teaches behaviour and format, not changing facts"]),
    S("EndCard", "Next, parameter-efficient fine-tuning: LoRA and its family, and why it became the default. And when you are ready to run it: lesson seventeen, lab T2. Check the data, then train.",
      line="Lesson 17 · Lab T2 — check the data, then train"),
]}

# ───────────────────────────── 16 · PEFT ─────────────────────────────
V["peft"] = {"title": "Parameter-Efficient Fine-Tuning", "subtitle": "LoRA and its family", "accent": "teal", "scenes": [
    title(16, "PEFT and LoRA", "Parameter-efficient fine-tuning",
          "how LoRA works, the arithmetic behind its size, and when to pick QLoRA, DoRA or the others",
          "Parameter-efficient fine-tuning, or PEFT, is a family of tricks that lets you customise a huge model by training a tiny fraction of it. LoRA is the famous one. It is the default on almost every platform, including Fireworks."),
    S("WeightUpdate", "Here is the idea. Take one weight matrix inside the model, say four thousand by four thousand. Freeze it. Beside it, add two thin matrices, B and A, that multiply together into a correction of the same shape. Only B and A train. The layer's output becomes the original output plus a small learned adjustment.",
      mode="lora", note="output = W·x + (α / r) · B·A·x  ·  W never changes"),
    S("Worked", "Do the arithmetic. The full matrix holds about sixteen point eight million numbers. With a rank of sixteen, A and B hold about sixty-five thousand each, under one percent of that matrix. Across a whole eight billion parameter model, adapting the attention projections, that is a fraction of one percent of all weights. The rank is the dial: higher rank means more capacity and more memory.",
      heading="Worked example · the size of one adapter", scenario="one 4096 × 4096 projection · rank r = 16",
      rows=[["full matrix W", "16.8 M"], ["LoRA A  (r × 4096)", "65,536"], ["LoRA B  (4096 × r)", "65,536"], ["trainable share", "0.8% of this matrix"], ["whole 8B model, attention only", "≈ 0.2–0.5% of weights"]],
      answer="Rank r is the dial: bigger r, more capacity, more memory"),
    S("Bullets", "Why does something so small work? Because the change a fine-tune needs tends to be low rank: a few directions in weight space matter, not all of them. The frozen base keeps its general knowledge, which also reduces forgetting. And after training you can merge the adapter into the weights for zero extra latency, or keep it separate as a tiny file.",
      heading="Why it works",
      items=["The change a fine-tune needs is low-rank: a few directions matter", "The frozen base keeps its general knowledge", "Merge for zero extra latency, or keep a tiny swappable file"]),
    S("CardGrid", "LoRA has relatives. QLoRA runs LoRA on top of a four-bit base model to save memory. DoRA separates each weight into a magnitude and a direction and applies LoRA to the direction, which often adds a point or two for a small speed cost. Adapter layers insert tiny bottleneck blocks. Prefix and prompt tuning learn virtual tokens instead of weights. And IA3 learns simple scaling vectors, the smallest of all.",
      heading="The PEFT family", cols=3,
      cards=[["LoRA", "two low-rank matrices beside frozen weights", "the default"], ["QLoRA", "LoRA on a 4-bit quantized base", "big models, small memory"], ["DoRA", "magnitude + direction; LoRA on direction", "often +1–2 pts, slower"],
             ["Adapters", "small bottleneck layers in each block", "older; adds latency"], ["Prefix / prompt tuning", "learn virtual tokens, not weights", "tiny; weaker on hard tasks"], ["IA³", "learn per-channel scaling vectors", "smallest of all"]]),
    S("BeforeAfter", "Choosing is mostly about constraints. If memory is the limit, move from LoRA to QLoRA. If there is still a quality gap against full fine-tuning, try DoRA or a higher rank. And if you have hundreds of customers, each with their own tune, keep the adapters separate and serve them with multi-LoRA.",
      heading="Choosing a variant", beforeLabel="default", afterLabel="switch to",
      rows=[["memory is the limit", "LoRA", "QLoRA"], ["quality gap vs full", "LoRA r = 16", "DoRA / higher r"], ["hundreds of tenants", "merged models", "multi-LoRA"]]),
    S("Worked", "This is where PEFT changes the business. Fifty customers with fifty full fine-tunes means fifty sixteen-gigabyte models and fifty deployments. Fifty LoRA adapters are about forty megabytes each and can all be served from one deployment, with the right adapter chosen per request. The serving bill is roughly one deployment instead of fifty.",
      heading="Worked example · 50 tenants", scenario="one 8B base · one tune per customer",
      rows=[["50 full fine-tunes", "50 × 16 GB · 50 deployments"], ["50 LoRA adapters", "50 × 40 MB · one deployment"], ["per request", "the right adapter is applied"], ["serving bill", "≈ 1 deployment, not 50"]],
      answer="Multi-LoRA makes per-customer tuning affordable"),
    S("Bullets", "The knobs are few. Rank: eight to sixteen for narrow tasks, thirty-two to sixty-four for harder ones. Alpha, a scaling factor usually set to about twice the rank. Which modules to adapt: attention only, or attention plus the feed-forward layers for more capacity. And how many layers, where adapting only the last few saves memory.",
      heading="The knobs",
      items=["rank r: 8–16 narrow tasks · 32–64 harder ones", "alpha: scaling, often ≈ 2 × r", "targets: attention only, or attention + MLP", "layers: last N only saves memory (mlx: --num-layers)"]),
    S("CommandCard", "Lesson seventeen has a calculator that prints the trainable parameters for any model and rank. Then it trains full, LoRA and DoRA on the same data, so you can see memory, time, adapter size and accuracy in one table.",
      heading="Run it · lesson 17",
      lines=["python peft_params.py --model 8b --rank 16", "python peft_params.py --model 70b --rank 64 --mlp", "bash run_variants.sh        # full · lora · dora", "python compare_variants.py  # one table"]),
    S("Recap", "Three things to take away. LoRA freezes the weights and trains a low-rank correction beside them. It touches under one percent of the parameters and gets close to full fine-tuning on narrow tasks. And pick QLoRA for memory, DoRA for quality, and multi-LoRA for many tenants.",
      heading="Recap", items=["LoRA freezes W and trains a low-rank B·A beside it", "<1% of parameters, near-full quality on narrow tasks", "QLoRA for memory · DoRA for quality · multi-LoRA for tenants"]),
    S("EndCard", "Next, preference alignment, starting with RLHF, the technique that made chat models helpful. And when you are ready to run it: lesson seventeen, lab T2.",
      line="Lesson 17 · Lab T2 — the PEFT calculator, then three runs"),
]}

# ───────────────────────────── 17 · RLHF ─────────────────────────────
V["rlhf"] = {"title": "RLHF", "subtitle": "Reinforcement learning from human feedback", "accent": "copper", "scenes": [
    title(17, "RLHF", "Reinforcement learning from human feedback",
          "why imitation is not enough, the three stages of RLHF, and what the KL leash is for",
          "Supervised fine-tuning teaches a model to imitate. But for many tasks there is no single right answer, only better and worse ones. Reinforcement learning from human feedback, RLHF, is how models learn that difference. It is the technique behind the first helpful chat assistants."),
    S("PrefPair", "Here is why. A customer writes in, angry about an outage. Answer A apologises, explains the cause, and offers a fix and a credit. Answer B is a technically accurate root cause with no apology and no next step. Both are correct. Writing the perfect reply is hard, but anyone can say which of these two is better. RLHF learns from exactly that kind of judgement.",
      heading="Why preferences, not answers", prompt="Customer: “Your outage cost us a day. Explain.”",
      chosen="Apologises, gives cause and timeline, states the fix and offers a credit.", rejected="Accurate root-cause paragraph. No apology, no next step.",
      note="Both are correct. People struggle to write the perfect answer, but easily pick the better one."),
    S("RlhfLoop", "RLHF has three stages. Stage one: start from a supervised fine-tuned model, one that already follows instructions and gives reasonable answers. You cannot reinforce behaviour the model never produces.", stage=0),
    S("RlhfLoop", "Stage two: collect comparisons. The model writes two answers to each prompt, and people pick the better one. Those choices train a reward model, a copy of the language model that outputs a single number. It learns to predict which answer a person would prefer, so it can score any new answer without a person in the loop.", stage=1),
    S("Worked", "Concretely, the reward model might score the empathetic answer two point one and the curt one minus zero point four. The difference, passed through a sigmoid, says there is about a ninety-two percent chance a person prefers A. That is the Bradley-Terry model, trained on tens of thousands of human comparisons.",
      heading="Worked example · the reward model's job", scenario="prompt: the outage complaint",
      rows=[["answer A · apology, cause, fix, credit", "score 2.1"], ["answer B · accurate, no apology", "score −0.4"], ["P(person prefers A) = σ(2.1 + 0.4)", "≈ 92%"], ["training data", "tens of thousands of comparisons"]],
      answer="The reward model turns human judgement into a number an optimizer can chase"),
    S("RlhfLoop", "Stage three is the reinforcement learning loop, usually with an algorithm called PPO. The model, now called the policy, writes answers. The reward model scores them. The policy is updated to make high-scoring answers more likely. Round and round, many thousands of times.", stage=2),
    S("Bullets", "There is a catch. The reward model only approximates human taste, and a policy that optimises it hard will find loopholes: flattery, padding, repeating phrases the reward model likes. This is called reward hacking. The fix is a leash. A KL penalty charges the policy for drifting too far from the original model, and beta sets the length of the leash.",
      heading="The KL leash",
      items=["Reward models are imperfect, and can be gamed", "Unleashed: flattery, padding, repeated phrases (reward hacking)", "KL penalty: pay for drifting from the reference model", "β = leash length: too tight learns nothing, too loose hacks"]),
    S("BeforeAfter", "It works, but it is heavy. Supervised fine-tuning needs one model in memory. PPO needs four: the policy, a frozen reference, the reward model and a value model. It needs lots of human comparisons, and it has many hyperparameters and can be unstable. That cost is exactly why the next technique, DPO, was invented.",
      heading="What RLHF costs", beforeLabel="SFT", afterLabel="RLHF with PPO",
      rows=[["models in memory", "1", "4"], ["human data", "prompt + answer", "ranked comparisons"], ["stability", "simple loss", "many knobs, can diverge"]],
      note="Four models: policy, frozen reference, reward model, value model."),
    S("CardGrid", "The family has grown. RLAIF replaces human labellers with an AI judge. GRPO, used for many reasoning models, compares a group of answers against each other and drops the value model. And reinforcement fine-tuning with graders uses a program to score each answer, such as tests passing or an exact match. Fireworks offers that as RFT.",
      heading="The reinforcement family today", cols=2,
      cards=[["RLHF + PPO", "human preferences → reward model → PPO", "the original recipe"], ["RLAIF", "an AI judge replaces human labels", "cheaper labels"],
             ["GRPO", "score a group of answers against each other; no value model", "popular for reasoning"], ["RFT with graders", "a program scores 0–1: tests pass, JSON valid, answer matches", "Fireworks RFT"]]),
    S("CommandCard", "Lesson sixteen runs the entire RLHF pipeline on a toy problem, in pure numpy, in a few seconds. It does supervised fine-tuning, fits a reward model to preference pairs, and optimises a policy with and without the KL leash, so you can watch reward hacking happen. Lesson eighteen points to the real trainers.",
      heading="Run it · lesson 16 (toy) and 18",
      lines=["# the whole RLHF pipeline in numpy, seconds", "python lessons/16-training-toy/toy_alignment.py", "python lessons/16-training-toy/toy_alignment.py --beta 0", "", "# real PPO / GRPO on a Mac (optional, advanced)", "pip install mlx-lm-lora"]),
    S("Recap", "Three things to take away. RLHF learns from comparisons when there is no single right answer. It runs in three stages: supervised fine-tuning, a reward model, then PPO with a KL leash. And it is powerful but heavy: four models and many knobs.",
      heading="Recap", items=["RLHF learns from comparisons when no single answer is right", "SFT → reward model → PPO, with a KL leash", "Powerful but heavy: four models, many knobs"]),
    S("EndCard", "Next, DPO, which gets most of the benefit of RLHF with none of the reinforcement learning machinery. And when you are ready to run it: lesson sixteen, lab T1.",
      line="Lesson 16 · Lab T1 — watch reward hacking in a toy RLHF"),
]}

# ───────────────────────────── 18 · DPO ─────────────────────────────
V["dpo"] = {"title": "Direct Preference Optimization", "subtitle": "RLHF's result, without the RL", "accent": "teal", "scenes": [
    title(18, "DPO", "Direct preference optimization",
          "how DPO learns from pairs, what β does, and how to build preference data from your own product",
          "Direct preference optimization, DPO, is the shortcut. It learns from the same preference pairs as RLHF, but skips the reward model and the reinforcement loop entirely. Today it is one of the most common ways teams align a model to their taste."),
    S("Bullets", "The insight, from a twenty twenty-three paper, is mathematical. The best possible policy under the RLHF objective can be written in terms of the reward, which means the reward can be written in terms of the policy. Substitute that in, and you can train straight on preference pairs with a simple loss: no reward model and no sampling loop.",
      heading="The insight",
      items=["RLHF's optimal policy has a closed form in terms of the reward", "So the reward can be expressed with the policy itself", "Train directly on pairs with a classification-style loss"]),
    S("DpoShift", "Here is what that loss does. For each pair, it compares how likely the model makes the chosen answer and the rejected one, each relative to a frozen reference copy. Training pushes the chosen answer up and the rejected one down. Beta controls how far it may move from the reference: the same leash as before, built into the loss.",
      note="β is the leash from RLHF, built into the loss."),
    S("BeforeAfter", "Side by side with PPO: two models in memory instead of four, no separate reward model, no sampling during training, and a training loop about as stable as supervised fine-tuning. That simplicity is why it spread so quickly.",
      heading="DPO vs RLHF with PPO", beforeLabel="RLHF + PPO", afterLabel="DPO",
      rows=[["models in memory", "4", "2 (policy + reference)"], ["reward model", "trained separately", "implicit"], ["sampling in training", "yes · slow", "no"], ["stability", "many knobs", "close to SFT"]]),
    S("PrefPair", "Where do pairs come from? Often, from your own product. When a support agent edits a model's draft, the edited version is chosen and the original is rejected. A thumbs-down, a regenerate or a correction all create pairs. Here, the concise, valid JSON is chosen, and the chatty answer that breaks the parser is rejected.",
      heading="Preference data from your own product", prompt="Ticket: “Card declined twice, launch is tomorrow.”",
      chosen='{"category": "billing", "severity": 4, "next_action": "route to billing"}', rejected="Sure! This looks like a billing issue, and I'd say it's fairly urgent…",
      note="Chosen: what an agent approved. Rejected: what they edited, or a thumbs-down."),
    S("Worked", "One step, with numbers. Relative to the reference, the chosen answer has become zero point eight more likely in log terms, and the rejected one zero point four less. The margin is one point two, and times a beta of zero point one gives zero point one two. The loss is minus log sigmoid of that: about zero point six three, down from zero point six nine when both were equal. More separation means lower loss.",
      heading="Worked example · one DPO step", scenario="β = 0.1 · log-probabilities relative to the reference",
      rows=[["chosen:   log π − log π_ref", "+0.8"], ["rejected: log π − log π_ref", "−0.4"], ["β × margin", "0.1 × 1.2 = 0.12"], ["loss = −log σ(0.12)", "0.63  (0.69 at start)"]],
      answer="The loss falls as chosen and rejected pull apart", answerLabel="Read it"),
    S("Bullets", "A few rules. Do supervised fine-tuning first: DPO refines behaviour, it does not teach the task. Make pairs differ in the thing you care about, not in random noise. Start beta around zero point one. And evaluate both the win rate against the old model and the task accuracy, because improving taste can quietly cost correctness.",
      heading="Getting DPO right",
      items=["SFT first: DPO refines a model that already does the task", "Pairs should differ in the thing you care about", "Start β ≈ 0.1; lower moves further from the reference", "Measure win-rate AND task accuracy"]),
    S("CardGrid", "There are relatives. IPO regularises against over-fitting the pairs. KTO learns from single thumbs up or down, no pairs needed. ORPO folds supervised fine-tuning and preference into one step with no reference model, and Fireworks supports it alongside DPO. SimPO is reference-free and length-normalised.",
      heading="DPO's relatives", cols=2,
      cards=[["IPO", "regularises against over-fitting the pairs", ""], ["KTO", "single thumbs-up / thumbs-down, no pairs", ""],
             ["ORPO", "SFT + preference in one step, no reference model", "Fireworks: --loss-method ORPO"], ["SimPO", "reference-free, length-normalised", ""]]),
    S("CommandCard", "In lesson eighteen you build pairs from the ticket data, train DPO on your Mac with MLX, optionally run the same job on Fireworks with one command, and compare valid-JSON rate, accuracy and answer length before and after.",
      heading="Run it · lesson 18",
      lines=["python make_pairs.py            # pairs from the ticket data", "bash dpo_mlx.sh                 # mlx_lm_lora --train-mode dpo", "bash dpo_fireworks.sh           # firectl dpo-job create", "python pref_eval.py --target mlx"]),
    S("Recap", "Three things to take away. DPO learns from chosen and rejected pairs with a simple loss. It needs two models, no reward model and no reinforcement loop, so it is nearly as stable as supervised fine-tuning. And do SFT first, then DPO, and measure both win rate and task accuracy.",
      heading="Recap", items=["DPO learns from chosen / rejected pairs with a simple loss", "Two models, no reward model, no RL loop: nearly as stable as SFT", "SFT first, then DPO; measure win-rate and accuracy"]),
    S("EndCard", "That completes the training series: full fine-tuning, supervised fine-tuning, LoRA and its family, RLHF, and DPO. When you are ready to run it: lesson eighteen, lab T3, DPO on your Mac and on Fireworks.",
      line="Lesson 18 · Lab T3 — DPO on your Mac and on Fireworks"),
]}

# ───────────── fix the existing 13: kickers "of 18" and end cards → lessons + current lab ids ─────────────
END = {
    "inference-101": ("Lesson 01 · Lab F1 — build your own TTFT and ITL harness", "lesson one, lab F1: build your own TTFT and ITL harness."),
    "kv-cache": ("Lesson 05 · Lab L5 — push context until it breaks, then fix it", "lesson five, lab L5: push context until it breaks, then fix it."),
    "gpu-bandwidth": ("Lessons 03–04 · Labs L3, L4 — sweep, then check the ceiling", "lessons three and four, labs L3 and L4: run the concurrency sweep, then check it against the ceiling."),
    "quantization": ("Lesson 04 · Lab L4 — three precisions, measured", "lesson four, lab L4: three precisions of one model, measured."),
    "batching": ("Lessons 03 & 13 · Labs L3, F7 — sweep, then add speculation", "lessons three and thirteen, labs L3 and F7: sweep concurrency, then add speculation."),
    "training": ("Lessons 10–11 · Labs F5, L8 — one fine-tune, managed and local", "lessons ten and eleven, labs F5 and L8: the same fine-tune, managed and local. The training deep dives follow in videos fourteen to eighteen."),
    "offloading": ("Lesson 12 · Lab L7 — MoE active bytes from decode speed", "lesson twelve, lab L7: measure MoE active bytes from decode speed."),
}
FULL_END = {  # videos whose end-card narration is written from scratch
    "platform": ("Lesson 15 · Capstone — one POC, one benchmark, one sizing memo",
                 "That is the whole map. Now go and build it, because the fastest way to sound credible is to have actually run it. When you are ready: lesson fifteen, the capstone. One POC, one benchmark, one sizing memo."),
    "serving-stack": ("Lessons 02 & 14 · Labs L2, L9 — serve it, then benchmark it",
                      "Run lesson two, lab L2, to get servers up on your Mac, and lesson fourteen, lab L9, for vLLM and SGLang on the Spark. Then benchmark them in lesson three."),
    "benchmarking": ("Lesson 03 · Lab L3 — the concurrency sweep",
                     "Run lesson three, lab L3, and keep the output. It becomes the first exhibit in your capstone memo."),
    "prefix-caching": ("Lesson 06 · Labs L6, F2 — measure it, then price it",
                       "Lesson six measures this on your own hardware with lab L6, and lab F2 shows the billing side on Fireworks."),
    "qlora": ("Lessons 11 & 10 · Labs L8, F5 — run both",
              "Lesson eleven, lab L8, runs this locally. Lesson ten, lab F5, runs the same dataset through Fireworks. For the full picture of training methods, see videos fourteen to eighteen."),
    "scale-out": ("Lessons 13–14 · Labs F7, L9 — speculation, then multi-node",
                  "Lessons thirteen and fourteen close out the serving track. Then come the training deep dives, videos fourteen to eighteen, and the capstone."),
}
KICK_SUFFIX = {"serving-stack": " · L2 and L9", "benchmarking": " · L3", "prefix-caching": " · L6 and F2", "qlora": " · L8 and F5", "scale-out": " · F7 and L9"}

changed = {}
for i, (vid, v) in enumerate(list(d.items()), start=1):
    t = v["scenes"][0]
    t["params"]["kicker"] = f"Video {i} of 18" + KICK_SUFFIX.get(vid, "")
    e = v["scenes"][-1]
    if vid in END:
        line, tail = END[vid]
        head = e["text"].split(" And when you are ready to run it:")[0]
        e["params"]["line"] = line
        e["text"] = f"{head} And when you are ready to run it: {tail}"
    elif vid in FULL_END:
        e["params"]["line"], e["text"] = FULL_END[vid]
    changed[vid] = [0, len(v["scenes"]) - 1]

d.update(V)
P.write_text(json.dumps(d, indent=2, ensure_ascii=False))
Path(P.parent.parent / "scripts" / ".changed_scenes.json").write_text(json.dumps(changed))
print(f"{len(d)} videos; new: {list(V)}")
for k, v in V.items():
    print(k, len(v["scenes"]), "scenes", sum(len(s["text"].split()) for s in v["scenes"]), "words")
