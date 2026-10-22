"""Math and parsers for the episode 1 KV cache kit. No network, no model download."""

from __future__ import annotations

import io
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EP))

import kv_cache  # noqa: E402
import measure_kv  # noqa: E402

GIB = 1024**3


def _pack_string(text: str) -> bytes:
    data = text.encode("utf-8")
    return struct.pack("<Q", len(data)) + data


def _pack_typed(value):
    if isinstance(value, str):
        return struct.pack("<I", 8) + _pack_string(value)
    if isinstance(value, list):
        body = struct.pack("<I", 9) + struct.pack("<I", 4) + struct.pack("<Q", len(value))
        for item in value:
            body += struct.pack("<I", item)
        return body
    if isinstance(value, int):
        return struct.pack("<I", 4) + struct.pack("<I", value)
    raise TypeError(type(value))


def _gguf(meta: dict) -> bytes:
    body = b""
    for key, value in meta.items():
        body += _pack_string(key) + _pack_typed(value)
    header = b"GGUF" + struct.pack("<I", 3) + struct.pack("<QQ", 1, len(meta))
    return header + body + b"tensor-bytes-that-must-not-be-required"


class FormulaTest(unittest.TestCase):
    def test_worked_example_is_4_gib(self):
        self.assertEqual(kv_cache.kv_bytes(32, 32, 128, 2, 8192), 4 * GIB)
        self.assertEqual(kv_cache.kv_bytes(32, 32, 128, 2.0, 8192), 4 * GIB)

    def test_gqa_shrinks_the_same_shape_to_1_gib(self):
        self.assertEqual(kv_cache.kv_bytes(32, 8, 128, 2, 8192), GIB)

    def test_quantized_widths_are_half_and_quarter(self):
        full = kv_cache.kv_bytes(32, 32, 128, 2, 8192)
        self.assertEqual(kv_cache.kv_bytes(32, 32, 128, 1, 8192), full // 2)
        self.assertEqual(kv_cache.kv_bytes(32, 32, 128, 0.5, 8192), full // 4)

    def test_qwen_shape_from_the_episode(self):
        per_token = kv_cache.kv_bytes(28, 4, 128, 2, 1)
        self.assertEqual(per_token, 56 * 1024)
        self.assertEqual(kv_cache.kv_bytes(28, 4, 128, 2, 8192), int(0.4375 * GIB))
        self.assertEqual(kv_cache.kv_bytes(28, 4, 128, 2, 32768, 4), 7 * GIB)

    def test_context_doubles_the_cache(self):
        short = kv_cache.kv_bytes(28, 4, 128, 2, 8192)
        self.assertEqual(kv_cache.kv_bytes(28, 4, 128, 2, 16384), short * 2)

    def test_rejects_a_shape_gqa_cannot_describe(self):
        with self.assertRaises(ValueError):
            kv_cache.shape_from_counts(layers=32, attention_heads=32, kv_heads=3, head_dim=128)


class ReportTest(unittest.TestCase):
    def test_example_prints_the_formula_and_both_shapes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = kv_cache.main(["--example"])
        text = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn(kv_cache.FORMULA, text)
        self.assertIn("2 x 32 x 32 x 128 x 2 x 8192 = 4 GiB", text)
        self.assertIn("2 x 32 x 8 x 128 x 2 x 8192 = 1 GiB", text)
        self.assertIn("4 query heads share one KV head", text)
        self.assertIn("q8_0", text)
        self.assertIn("2 GiB", text)
        self.assertIn("not a measurement", text)

    def test_cli_entrypoint(self):
        proc = subprocess.run(
            [sys.executable, str(EP / "kv_cache.py"), "--example"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("2 x 32 x 32 x 128 x 2 x 8192 = 4 GiB", proc.stdout)

    def test_manual_quantized_table(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = kv_cache.main(
                [
                    "--layers",
                    "32",
                    "--attention-heads",
                    "32",
                    "--kv-heads",
                    "32",
                    "--head-dim",
                    "128",
                    "--tokens",
                    "8192",
                    "--contexts",
                    "8192",
                ]
            )
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("4 GiB", text)
        self.assertIn("2 GiB", text)
        self.assertIn("1 GiB", text)


class ShapeReadersTest(unittest.TestCase):
    def test_config_derives_head_dim_and_keeps_kv_heads(self):
        shape = kv_cache.shape_from_config(
            {
                "num_hidden_layers": 28,
                "num_attention_heads": 28,
                "num_key_value_heads": 4,
                "hidden_size": 3584,
                "head_dim": None,
                "torch_dtype": "bfloat16",
            }
        )
        self.assertEqual(shape.layers, 28)
        self.assertEqual(shape.attention_heads, 28)
        self.assertEqual(shape.kv_heads, 4)
        self.assertEqual(shape.head_dim, 128)
        self.assertEqual(shape.bytes_per_value, 2)
        self.assertEqual(shape.dtype_name, "bf16")
        self.assertIn("hidden size", shape.head_dim_note)
        self.assertEqual(shape.group_size, 7)
        report = kv_cache.render_report(shape, tokens=8192, contexts=(8192,))
        self.assertIn("2 x 28 x 4 x 128 x 2 x 8192 = 0.4375 GiB", report)
        self.assertIn("56 KiB", report)

    def test_config_nested_text_block(self):
        shape = kv_cache.shape_from_config(
            {"text_config": {"num_hidden_layers": 16, "num_attention_heads": 8, "num_key_value_heads": 2, "head_dim": 64}}
        )
        self.assertEqual((shape.layers, shape.kv_heads, shape.head_dim), (16, 2, 64))

    def test_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "num_hidden_layers": 32,
                        "num_attention_heads": 32,
                        "num_key_value_heads": 32,
                        "head_dim": 128,
                    }
                ),
                encoding="utf-8",
            )
            shape = kv_cache.load_config(path)
        self.assertEqual(kv_cache.kv_bytes_for(shape, 8192), 4 * GIB)

    def test_gguf_metadata_and_trailing_tensor_bytes(self):
        meta = {
            "general.architecture": "llama",
            "llama.block_count": 32,
            "llama.attention.head_count": [32, 32],
            "llama.attention.head_count_kv": 8,
            "llama.embedding_length": 4096,
            "llama.attention.key_length": 64,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.gguf"
            path.write_bytes(_gguf(meta))
            shape = kv_cache.load_gguf(path)
        self.assertEqual(shape.head_dim, 64)
        self.assertEqual(shape.kv_heads, 8)
        self.assertEqual(shape.attention_heads, 32)
        self.assertEqual(shape.group_size, 4)
        self.assertNotIn("embedding length", shape.head_dim_note)

    def test_gguf_derives_head_dim_when_key_length_is_absent(self):
        meta = {
            "general.architecture": "llama",
            "llama.block_count": 32,
            "llama.attention.head_count": 32,
            "llama.attention.head_count_kv": 8,
            "llama.embedding_length": 4096,
        }
        shape = kv_cache.shape_from_gguf_metadata(meta)
        self.assertEqual(shape.head_dim, 128)
        self.assertIn("embedding length", shape.head_dim_note)
        self.assertEqual(kv_cache.kv_bytes_for(shape, 8192), GIB)

    def test_gguf_rejects_a_layerwise_head_count(self):
        meta = {
            "general.architecture": "llama",
            "llama.block_count": 2,
            "llama.attention.head_count": [32, 16],
            "llama.embedding_length": 4096,
        }
        with self.assertRaises(ValueError):
            kv_cache.shape_from_gguf_metadata(meta)

    def test_not_a_gguf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.gguf"
            path.write_bytes(b"not a model")
            with self.assertRaises(ValueError):
                kv_cache.load_gguf(path)

    def test_ollama_show_keeps_weight_quant_off_the_cache_width(self):
        shape = kv_cache.shape_from_ollama_show(
            {
                "details": {"quantization_level": "Q4_K_M"},
                "model_info": {
                    "general.architecture": "llama",
                    "llama.block_count": 32,
                    "llama.attention.head_count": 32,
                    "llama.attention.head_count_kv": 8,
                    "llama.embedding_length": 4096,
                },
            },
            name="example",
        )
        self.assertEqual(shape.bytes_per_value, 2)
        self.assertEqual(shape.weight_quant, "Q4_K_M")
        report = kv_cache.render_report(shape, tokens=8192, contexts=(8192,))
        self.assertIn("Q4_K_M", report)
        self.assertIn("does not set the cache width", report)
        self.assertIn("2 x 32 x 8 x 128 x 2 x 8192 = 1 GiB", report)


class MeasureHelpersTest(unittest.TestCase):
    def test_large_model_names(self):
        self.assertFalse(measure_kv.model_is_large("llama3.2:1b"))
        self.assertFalse(measure_kv.model_is_large("qwen2.5:0.5b"))
        self.assertFalse(measure_kv.model_is_large("llama3.2:3b"))
        self.assertTrue(measure_kv.model_is_large("qwen2.5:7b"))
        self.assertTrue(measure_kv.model_is_large("llama3.1:8b"))
        self.assertTrue(measure_kv.model_is_large("llama3.1:70b"))
        self.assertTrue(measure_kv.model_is_large("mixtral:8x7b"))
        self.assertTrue(measure_kv.model_is_large("gemma2:27b"))

    def test_install_plan_never_downloads_without_pull(self):
        missing = measure_kv.plan_install("llama3.2:1b", [], pull=False)
        self.assertEqual(missing.action, "refuse")
        self.assertIn("Nothing was downloaded", missing.reason)
        large = measure_kv.plan_install("qwen2.5:7b", [], pull=False)
        self.assertEqual(large.action, "refuse")
        self.assertIn("large", large.reason)
        ready = measure_kv.plan_install("llama3.1:70b", ["llama3.1:70b"], pull=False)
        self.assertEqual(ready.action, "ready")
        pulled = measure_kv.plan_install("qwen2.5:7b", [], pull=True)
        self.assertEqual(pulled.action, "pull")
        self.assertIn("--pull", pulled.reason)
        small = measure_kv.plan_install("llama3.2:1b", [], pull=True)
        self.assertEqual(small.action, "pull")
        self.assertEqual(small.reason, "")

    def test_tag_match_does_not_confuse_siblings(self):
        installed = ["llama3.2:1b", "llama3.2:3b", "qwen2.5:latest"]
        self.assertTrue(measure_kv.is_installed(installed, "llama3.2:1b"))
        self.assertFalse(measure_kv.is_installed(installed, "llama3.2:8b"))
        self.assertTrue(measure_kv.is_installed(installed, "qwen2.5"))
        self.assertFalse(measure_kv.is_installed(installed, "llama3.2"))

    def test_nvidia_smi_and_ps_parsers(self):
        self.assertIsNone(measure_kv.parse_nvidia_smi(""))
        self.assertIsNone(measure_kv.parse_nvidia_smi("[N/A]\n"))
        self.assertEqual(measure_kv.parse_nvidia_smi("1024\n2048\n"), 3072 * 1024 * 1024)
        self.assertIsNone(measure_kv.parse_nvidia_smi("nope\n"))
        text = "1000 ollama\n2000 ollama runner\n50 sshd\n"
        self.assertEqual(measure_kv.parse_ps_rss(text), 3000 * 1024)
        self.assertIsNone(measure_kv.parse_ps_rss("50 sshd\n"))

    def test_safe_detail_drops_paths(self):
        self.assertEqual(measure_kv.safe_detail("model runner stopped"), "model runner stopped")
        self.assertEqual(measure_kv.safe_detail("missing /tmp/models/blob"), "Ollama refused the request.")

    def test_row_uses_the_formula(self):
        shape = kv_cache.example_shapes()[0]
        row = measure_kv.build_row(
            num_ctx=8192,
            shape=shape,
            measured_runtime_bytes=None,
            measured_vram_bytes=None,
            gpu_memory_bytes=None,
            process_rss_bytes=None,
            ttft_ms=12.34,
            load_ms=None,
            notes="",
        )
        self.assertEqual(row["predicted_kv_bytes"], 4 * GIB)
        self.assertEqual(row["ttft_ms"], 12.3)
        self.assertIsNone(row["measured_runtime_bytes"])

    def test_kv_type_override(self):
        self.assertEqual(measure_kv.bytes_for_kv_type(None)[:2], (2.0, "f16"))
        self.assertEqual(measure_kv.bytes_for_kv_type("q8_0")[:2], (1.0, "q8_0"))
        width, label, note = measure_kv.bytes_for_kv_type("weird")
        self.assertEqual((width, label), (2.0, "f16"))
        self.assertIsNotNone(note)

    def test_host_metrics_degrade(self):
        metrics = measure_kv.collect_host_metrics()
        self.assertIn(metrics["os"], {"Linux", "Darwin", "Windows"})
        self.assertTrue(metrics["gpu_memory_bytes"] is None or isinstance(metrics["gpu_memory_bytes"], int))
        self.assertIsInstance(metrics["notes"], list)

    def test_results_roundtrip(self):
        shape = kv_cache.example_shapes()[0]
        payload = {
            "model": "example shape",
            "source": "ollama",
            "rows": [
                measure_kv.build_row(
                    num_ctx=8192,
                    shape=shape,
                    measured_runtime_bytes=9 * GIB,
                    measured_vram_bytes=None,
                    gpu_memory_bytes=None,
                    process_rss_bytes=None,
                    ttft_ms=80,
                    load_ms=400,
                    notes="",
                )
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = measure_kv.write_results(Path(tmp) / "kv-sweep", payload)
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            csv_text = csv_path.read_text(encoding="utf-8")
        self.assertEqual(saved["rows"][0]["predicted_kv_bytes"], 4 * GIB)
        self.assertIn("predicted_kv_bytes", csv_text)
        self.assertIn(str(4 * GIB), csv_text)


class SampleAssetsTest(unittest.TestCase):
    def test_sample_measurements_match_the_formula(self):
        path = EP / "chart" / "src" / "sample-measurements.json"
        sample = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(sample["source"], "sample")
        shape = sample["shape"]
        baseline = 5 * GIB
        self.assertGreaterEqual(len(sample["rows"]), 4)
        for row in sample["rows"]:
            predicted = kv_cache.kv_bytes(
                shape["layers"],
                shape["kv_heads"],
                shape["head_dim"],
                shape["bytes_per_value"],
                row["num_ctx"],
            )
            self.assertEqual(row["predicted_kv_bytes"], predicted)
            self.assertEqual(row["measured_runtime_bytes"], predicted + baseline)
        eight_k = next(row for row in sample["rows"] if row["num_ctx"] == 8192)
        self.assertEqual(eight_k["predicted_kv_bytes"], 4 * GIB)

    def test_whiteboard_is_black_on_white_without_level_badges(self):
        path = EP / "whiteboard" / "kv-cache.excalidraw"
        scene = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(scene["type"], "excalidraw")
        self.assertEqual(scene["appState"]["viewBackgroundColor"].lower(), "#ffffff")
        texts = []
        for element in scene["elements"]:
            if element.get("isDeleted"):
                continue
            stroke = str(element.get("strokeColor", "")).lower()
            background = str(element.get("backgroundColor", "")).lower()
            self.assertIn(stroke, {"#000", "#000000", "transparent"})
            self.assertIn(background, {"#000", "#000000", "#fff", "#ffffff", "transparent"})
            if element.get("type") == "text":
                texts.append(element.get("text", ""))
        text = "\n".join(texts)
        self.assertIn(kv_cache.FORMULA, text)
        self.assertIn("4 GiB", text)
        self.assertIn("1 GiB", text)
        self.assertNotIn("L1", text)
        self.assertNotRegex(text.lower(), r"\blevel\b")


if __name__ == "__main__":
    unittest.main()
