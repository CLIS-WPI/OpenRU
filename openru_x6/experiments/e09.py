"""E09: GPU stress, model sensitivity and scaling limits."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch

from ..config import config_digest, load_assumptions
from ..energy import power_breakdown
from ..gpu import GpuMonitor
from .common import (make_context, make_result, params_for, record, run_engine)


def _time_matmul(n: int, iters: int = 8) -> dict:
    dev = torch.device("cuda")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    a = torch.randn(n, n, device=dev)
    b = torch.randn(n, n, device=dev)
    for _ in range(2):
        c = a @ b
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        c = a @ b
    torch.cuda.synchronize()
    elapsed = (time.perf_counter() - t0) / iters
    peak = torch.cuda.max_memory_allocated() / 2**30
    finite = bool(torch.isfinite(c).all().item())
    del a, b, c
    torch.cuda.empty_cache()
    return {"size": n, "mean_ms": elapsed * 1e3, "tflops": 2 * n**3 / elapsed / 1e12,
            "peak_gb": peak, "finite": finite}


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E09", suite)
    sizes = [int(x) for x in p.get("matmul_sizes", [1024, 4096])]
    sens = list(p.get("sensitivities", ["low", "base", "high"]))
    ue_counts = [int(x) for x in p.get("ue_counts", [64, 256])]
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    artifacts: dict[str, object] = {}
    checks["cuda_available"] = bool(torch.cuda.is_available())
    if not checks["cuda_available"]:
        res = make_result("E09", "GPU stress and sensitivity", t0,
                          {"cuda_visible": False}, {"error": "no CUDA device"})
        res.status = "BLOCKED"
        return res

    mat = []
    with GpuMonitor(interval_s=0.2) as mon:
        for n in sizes:
            try:
                mat.append(_time_matmul(n))
            except torch.cuda.OutOfMemoryError:
                mat.append({"size": n, "error": "OOM"})
                torch.cuda.empty_cache()
        gpu_summary = mon.summary()
    checks["matmul_finite"] = all(m.get("finite", False) for m in mat)
    checks["no_oom"] = all("error" not in m for m in mat)
    metrics["matmul"] = mat
    metrics["gpu_monitor"] = gpu_summary
    for m in mat:
        if "mean_ms" in m:
            store.add("E09", "gpu_matmul", 0, f"n{m['size']}", "mean_ms", m["mean_ms"], "ms",
                      "SIMULATED", digest)
            store.add("E09", "gpu_matmul", 0, f"n{m['size']}", "tflops", m["tflops"], "TFLOP/s",
                      "SIMULATED", digest)
    artifacts["matmul"] = mat

    assumptions = load_assumptions()
    powers = {}
    for level in sens:
        upd = {}
        for key, field in (("pa_efficiency", "pa_efficiency"),
                           ("per_chain_electronics_w", "per_chain_electronics_w"),
                           ("per_feed_branch_w", "per_feed_branch_w"),
                           ("dsp_fpga_w", "dsp_fpga_w"),
                           ("always_on_w", "always_on_w")):
            item = assumptions.assumptions.get(key)
            if item is not None:
                upd[field] = item.value if level == "base" else (item.low if level == "low" else item.high)
        e = energy.model_copy(update=upd)
        pb = power_breakdown(e, "FULL_64", 20.0)
        powers[level] = pb["total_w"]
        store.add("E09", "power_sensitivity", 0, level, "full_power_w", pb["total_w"], "W",
                  "SIMULATED", digest)
        metrics[f"power_{level}_w"] = pb["total_w"]
    checks["sensitivity_brackets_base"] = powers.get("low", 0) <= powers.get("base", 0) <= \
        powers.get("high", 0)
    artifacts["power_sensitivity"] = powers

    for U in ue_counts:
        ctx_t0 = time.perf_counter()
        ctx = make_context(radio, seed=909, n_users=U, n_slots=2, channel_update_slots=2,
                           saturate=True)
        build_s = time.perf_counter() - ctx_t0
        torch.cuda.reset_peak_memory_stats()
        run_t0 = time.perf_counter()
        r = run_engine(radio, energy, security, ctx, forced_chains=64, scheduler_policy="pf",
                       energy_kind="static")
        run_s = time.perf_counter() - run_t0
        peak = torch.cuda.max_memory_allocated() / 2**30
        store.add("E09", "ue_scaling", U, "pf", "context_build_s", build_s, "s", "SIMULATED",
                  digest)
        store.add("E09", "ue_scaling", U, "pf", "run_s", run_s, "s", "SIMULATED", digest)
        store.add("E09", "ue_scaling", U, "pf", "peak_vram_gb", peak, "GB", "SIMULATED", digest)
        store.add("E09", "ue_scaling", U, "pf", "sum_goodput_mbps",
                  r.summary["sum_goodput_mbps"], "Mbps", "SIMULATED", digest)
        metrics[f"ue{U}"] = {"context_build_s": build_s, "run_s": run_s, "peak_vram_gb": peak,
                             "sum_goodput_mbps": r.summary["sum_goodput_mbps"]}
        checks[f"ue{U}_finite"] = bool(np.isfinite(r.summary["sum_goodput_mbps"]))

    cell = radio.cell.model_copy(update={"bandwidth_hz": radio.cell.bandwidth_hz * 4.0,
                                         "n_rb_sim": 64})
    radio400 = radio.model_copy(update={"cell": cell})
    ctx = make_context(radio400, seed=910, n_users=64, n_slots=2, channel_update_slots=2,
                       saturate=True)
    t1 = time.perf_counter()
    r400 = run_engine(radio400, energy, security, ctx, forced_chains=64,
                      scheduler_policy="pf", energy_kind="static")
    t400 = time.perf_counter() - t1
    store.add("E09", "abstract_400mhz", 910, "pf", "sum_goodput_mbps",
              r400.summary["sum_goodput_mbps"], "Mbps", "SIMULATED", digest)
    store.add("E09", "abstract_400mhz", 910, "pf", "run_s", t400, "s", "SIMULATED", digest)
    metrics["abstract_400mhz"] = {"sum_goodput_mbps": r400.summary["sum_goodput_mbps"],
                                  "run_s": t400,
                                  "note": "abstract bandwidth scaling; not a 400 MHz hardware claim"}
    checks["abstract_400mhz_runs"] = bool(np.isfinite(r400.summary["sum_goodput_mbps"]))
    artifacts["abstract_400mhz"] = metrics["abstract_400mhz"]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "e09_gpu_sensitivity.json").write_text(json.dumps(artifacts, indent=2),
                                                      encoding="utf-8")
    checks["data_collected"] = bool(mat)
    res = make_result("E09", "GPU stress and model sensitivity", t0, checks, metrics)
    res.artifacts = ["e09_gpu_sensitivity.json"]
    return res
