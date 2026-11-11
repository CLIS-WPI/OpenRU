"""GPU discovery, environment provenance and runtime monitoring.

The lab never assumes that GPU 0 is free.  A physical GPU can be pinned with
``OPENRU_GPU_INDEX`` or by Compose device selection.  Only GPUs that are visible
inside the container are considered; unrelated host GPUs are untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], timeout: float = 10.0) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=timeout).strip()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"ERROR: {type(exc).__name__}: {exc}"


@dataclass
class GpuInfo:
    visible_index: int
    name: str
    uuid: str
    total_mb: float
    free_mb: float
    util_pct: float
    driver: str
    cuda_version: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def query_gpus() -> list[GpuInfo]:
    out = _run([
        "nvidia-smi",
        "--query-gpu=index,name,uuid,memory.total,memory.free,utilization.gpu,driver_version",
        "--format=csv,noheader,nounits",
    ])
    driver = ""
    cuda = ""
    header = _run(["nvidia-smi"])
    for line in header.splitlines():
        if "Driver Version" in line:
            try:
                driver = line.split("Driver Version:")[1].split()[0].strip()
                cuda = line.split("CUDA Version:")[1].split()[0].strip()
            except Exception:
                pass
    gpus: list[GpuInfo] = []
    if out.startswith("ERROR"):
        return gpus
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            gpus.append(GpuInfo(
                visible_index=int(parts[0]), name=parts[1], uuid=parts[2],
                total_mb=float(parts[3]), free_mb=float(parts[4]),
                util_pct=float(parts[5]), driver=driver, cuda_version=cuda,
            ))
        except ValueError:
            continue
    return gpus


def select_gpu(min_free_mb: float = 4096.0) -> GpuInfo | None:
    gpus = query_gpus()
    if not gpus:
        return None
    pinned = os.environ.get("OPENRU_GPU_INDEX")
    if pinned not in (None, ""):
        idx = int(pinned)
        for g in gpus:
            if g.visible_index == idx:
                return g
        raise RuntimeError(f"OPENRU_GPU_INDEX={idx} not visible; visible={[g.visible_index for g in gpus]}")
    eligible = [g for g in gpus if g.free_mb >= min_free_mb]
    if not eligible:
        eligible = gpus
    return sorted(eligible, key=lambda g: (g.util_pct, -g.free_mb))[0]


def torch_device_info() -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        return {"torch": None, "error": f"{type(exc).__name__}: {exc}"}
    info: dict[str, Any] = {
        "torch_version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": torch.version.cuda,
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    if torch.cuda.is_available():
        props = [torch.cuda.get_device_properties(i) for i in range(torch.cuda.device_count())]
        info["devices"] = [{"index": i, "name": p.name, "total_mem_gb": round(p.total_memory / 2**30, 2),
                            "cc": f"{p.major}.{p.minor}"} for i, p in enumerate(props)]
        info["selected"] = torch.cuda.get_device_name(0)
        info["selected_mem_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2)
        x = torch.randn(2048, 2048, device="cuda", dtype=torch.float32)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        y = x @ x
        torch.cuda.synchronize()
        info["sanity_matmul_ms"] = round((time.perf_counter() - t0) * 1e3, 3)
        info["sanity_matmul_sum"] = float(y.double().sum().item())
        info["peak_mem_gb_after_sanity"] = round(torch.cuda.max_memory_allocated() / 2**30, 4)
        del x, y
        torch.cuda.empty_cache()
    return info


def software_versions() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "utc": utc_now(),
        "cwd": os.getcwd(),
        "env_gpu_visible": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "env_nvidia_visible": os.environ.get("NVIDIA_VISIBLE_DEVICES"),
        "env_openru_gpu_index": os.environ.get("OPENRU_GPU_INDEX"),
    }
    for name in ("numpy", "scipy", "pandas", "pydantic", "matplotlib", "sionna"):
        try:
            mod = __import__(name)
            info[name] = getattr(mod, "__version__", "unknown")
        except Exception:
            info[name] = None
    try:
        import torch
        info["torch"] = torch.__version__
    except Exception:
        info["torch"] = None
    return info


def git_provenance(repo: Path) -> dict[str, Any]:
    sha = _run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    dirty = _run(["git", "-C", str(repo), "status", "--porcelain"])
    files = sorted(p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts
                   and "results" not in p.parts and "__pycache__" not in p.parts)
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(repo)).encode())
        h.update(p.read_bytes())
    return {
        "git_sha": None if sha.startswith("ERROR") else sha,
        "git_dirty": None if dirty.startswith("ERROR") else bool(dirty),
        "tree_sha256": h.hexdigest(),
        "n_files": len(files),
        "note": "git_sha is null when the delivered tree is not a git checkout; tree_sha256 is authoritative.",
    }


def image_digest() -> str | None:
    """Best-effort image digest via the container's image label/env (set by scripts)."""
    return os.environ.get("OPENRU_IMAGE_DIGEST")


class GpuMonitor:
    """Samples the visible GPU while a suite runs."""

    def __init__(self, interval_s: float = 0.5) -> None:
        self.interval_s = interval_s
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "GpuMonitor":
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.is_set():
            gpus = query_gpus()
            if gpus:
                g = gpus[0]
                self.samples.append({"t": utc_now(), "util_pct": g.util_pct, "mem_used_mb":
                                     round(g.total_mb - g.free_mb, 1), "mem_total_mb": g.total_mb,
                                     "temp_c": None, "power_w": None})
            self._stop.wait(self.interval_s)

    def __exit__(self, *exc: Any) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {"n_samples": 0}
        util = [s["util_pct"] for s in self.samples]
        mem = [s["mem_used_mb"] for s in self.samples]
        return {
            "n_samples": len(self.samples),
            "util_mean_pct": round(sum(util) / len(util), 2),
            "util_max_pct": max(util),
            "mem_peak_mb": max(mem),
            "mem_mean_mb": round(sum(mem) / len(mem), 1),
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.samples, indent=1), encoding="utf-8")


def environment_report(repo: Path) -> dict[str, Any]:
    return {
        "generated_utc": utc_now(),
        "software": software_versions(),
        "gpu_visible": [g.as_dict() for g in query_gpus()],
        "gpu_selected": (select_gpu().as_dict() if select_gpu() else None),
        "torch": torch_device_info(),
        "provenance": git_provenance(repo),
        "image_digest": image_digest(),
        "nvidia_smi": _run(["nvidia-smi"]),
        "docker_available": shutil.which("docker") is not None,
    }
