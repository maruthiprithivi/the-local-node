# Two Sparks: validate the fabric before you trust tensor parallelism

Two DGX Sparks can be linked through their ConnectX-7 ports to serve a model neither
can hold alone (for example a 200B+ model at 4-bit). Scaling out adds a new failure mode:
**the network**. Tensor parallelism does an all-reduce inside *every layer* for *every token*,
so a slow or misconfigured link wipes out the gain.

The field-engineer habit is to **measure the pipe first, then the model**.

## 1. Link up
- Cable the ConnectX-7 ports directly (QSFP). Give each side an IP on a private subnet.
- `ip addr`, `ethtool <iface> | grep Speed` should report the expected link speed.
- Set up passwordless SSH both ways, and use the same container image and model path on both boxes.

## 2. Raw bandwidth, then NCCL
```bash
# box A                          # box B
iperf3 -s                        iperf3 -c <A_IP> -P 8 -t 20        # TCP sanity check
# NCCL all-reduce across both boxes (from the NGC PyTorch container, nccl-tests built in or compiled):
mpirun -np 2 -H <A_IP>,<B_IP> ... all_reduce_perf -b 8M -e 1G -f 2 -g 1
```
Read **busbw** at large message sizes. If it is far below link speed, fix the network
(interface pinning with `NCCL_SOCKET_IFNAME`, RDMA/RoCE settings, MTU) before touching vLLM.

## 3. Only then: the model across two boxes
- Use vLLM with a Ray cluster spanning both boxes (`ray start --head` on A, `ray start --address=<A_IP>:6379` on B), then
  `vllm serve <model> --tensor-parallel-size 2` or `--pipeline-parallel-size 2`.
- Try **PP=2** as well as TP=2. Over a network link, pipeline parallelism (one hand-off per
  layer *block*) often beats tensor parallelism (an all-reduce every layer).
- Re-run `2_bench.sh`. Compare single-box performance on a model that fits with two-box
  performance on the same model. That overhead is the cost of scale-out.

## What to say
> "Before tensor parallel across nodes I validate the fabric with NCCL all-reduce busbw.
> Across a network I'd try pipeline parallel first; TP wants NVLink-class bandwidth."
