# Stock runtime compatibility boundary

Exact NVFP4 weights ran on pinned ARM64 vLLM and SGLang; Ollama could not import those exact safetensors on Linux ARM64: "MLX runtime is not available: failed to load MLX dynamic library". Official Ollama v0.40.15 has an amd64-mlx asset but no arm64-mlx release asset. This is a tested platform/format limitation, not proof that a future build cannot work.

Separate candidate: official qwen3.8:27b-q8_0 text-only GGUF, SHA256 2bb22714289826d7b9e0ba376c3ce47d08bce39abe598745857c44d88c09bdbf, 29047084384 bytes. Ollama imports it unchanged. Pinned vLLM's direct-file route attempted JSON config parsing; directory route failed "Unknown quantization method: gguf". Pinned SGLang --language-model-only rejects Qwen3_5ForConditionalGeneration; --language-only is encoder disaggregation and failed "Can not get local ip" under required network isolation. No architecture substitution, security weakening or source patch was attempted. Consequently no fair three-engine common-quant ranking qualified.

Next bounded engineering task: a source-controlled, reviewed ARM64/SM121-compatible Ollama MLX container build for exact safetensors, OR a vetted GGUF loader/standalone-text support investigation for these vLLM/SGLang builds. Deliver pinned OCI digest, build source, network-isolated import/start qualification, context/tokenizer/cache-reset/cache-hit assertions and projected memory bounds before timing. That work is outside this kit. Do not change network/AppArmor policy to make a loader pass.

References:
- https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B
- https://docs.ollama.com/docker
- https://docs.ollama.com/import
- https://ollama.com/library/qwen3.8:27b-nvfp4
- https://github.com/ollama/ollama/releases/tag/v0.40.15
