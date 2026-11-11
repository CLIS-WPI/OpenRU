"""Report and figure generation from executed experiment results."""
from __future__ import annotations

import base64
import html
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from .config import CONFIG_DIR
from .metrics import MetricsStore, bootstrap_ci, paired_delta_ci


STATUS_ORDER = {"PASS": 0, "FAIL": 1, "BLOCKED": 2, "NOT_RUN": 3, "ERROR": 4}


def _df(store: MetricsStore | pd.DataFrame) -> pd.DataFrame:
    if isinstance(store, pd.DataFrame):
        return store.copy()
    return store.dataframe()


def _vals(df: pd.DataFrame, exp: str, metric: str, **filters: Any) -> np.ndarray:
    sub = df[(df.experiment == exp) & (df.metric == metric)]
    for k, v in filters.items():
        if k not in sub.columns:
            continue
        sub = sub[sub[k] == v]
    return sub.value.to_numpy(dtype=float)


def _mean(df: pd.DataFrame, exp: str, metric: str, **filters: Any) -> float:
    x = _vals(df, exp, metric, **filters)
    x = x[np.isfinite(x)]
    return float(x.mean()) if x.size else float("nan")


def _ci(df: pd.DataFrame, exp: str, metric: str, **filters: Any) -> str:
    x = _vals(df, exp, metric, **filters)
    if x.size == 0:
        return "n/a"
    mean, lo, hi = bootstrap_ci(x)
    return f"{mean:.3g} [{lo:.3g}, {hi:.3g}]"


def _save(fig: plt.Figure, out: Path, name: str) -> list[str]:
    files = []
    for ext in ("png", "svg"):
        path = out / f"{name}.{ext}"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        files.append(path.name)
    plt.close(fig)
    return files


def _placeholder(out: Path, name: str, message: str) -> list[str]:
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=11)
    return _save(fig, out, name)


def _goodput_vs_ue(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E01") & (df.metric == "sum_goodput_mbps")]
    rows = []
    for _, r in sub.iterrows():
        sc = str(r.scenario)
        if not sc.startswith("chains"):
            continue
        try:
            chains = int(sc.split("_")[0].replace("chains", ""))
            users = int(sc.split("_ue")[1])
        except (ValueError, IndexError):
            continue
        rows.append((chains, users, float(r.value)))
    if not rows:
        return []
    d = pd.DataFrame(rows, columns=["chains", "users", "goodput"])
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for chains, g in d.groupby("chains"):
        m = g.groupby("users").goodput.mean()
        ax.plot(m.index, m.values, marker="o", label=f"{chains} chains")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("UEs")
    ax.set_ylabel("Sum goodput (Mbps)")
    ax.set_title("E01: sum goodput vs UE count and RF chain mode")
    ax.grid(alpha=0.3)
    ax.legend()
    return _save(fig, out, "fig_e01_goodput_vs_ue")


def _fairness(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E01") & (df.metric.isin(["jain_fairness", "p5_user_goodput_mbps"]))]
    if sub.empty:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, metric, title in zip(axes, ["jain_fairness", "p5_user_goodput_mbps"],
                                 ["Jain fairness", "5th-percentile user goodput (Mbps)"]):
        g = sub[sub.metric == metric].groupby("scenario").value.mean().sort_values()
        ax.barh(g.index[-12:], g.values[-12:])
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.3)
    fig.suptitle("E01: fairness and cell-edge service")
    fig.tight_layout()
    return _save(fig, out, "fig_e01_fairness_p5")


def _energy(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E02") & (df.metric.isin(["mean_power_w", "energy_j"]))]
    if sub.empty:
        return []
    sub = sub.copy()
    sub["load"] = sub.scenario.astype(str).str.extract(r"load([0-9.]+)").astype(float)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, metric, ylabel in zip(axes, ["mean_power_w", "energy_j"],
                                  ["Mean power (W)", "Energy (J)"]):
        s = sub[sub.metric == metric]
        for policy, g in s.groupby("policy"):
            m = g.groupby("load").value.mean()
            ax.plot(m.index, m.values, marker="o", label=policy)
        ax.set_xlabel("Normalized offered load")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
        if ax.get_legend_handles_labels()[0]:
            ax.legend()
    axes[0].set_title("E02: power vs load")
    axes[1].set_title("E02: energy vs load")
    fig.tight_layout()
    return _save(fig, out, "fig_e02_energy_vs_load")


def _bar_by(df: pd.DataFrame, exp: str, metric: str, out: Path, name: str, title: str,
            ylabel: str, policy: str | None = None) -> list[str]:
    sub = df[(df.experiment == exp) & (df.metric == metric)]
    if policy is not None:
        sub = sub[sub.policy == policy]
    if sub.empty:
        return []
    g = sub.groupby("scenario").value.mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(len(g)), g.values)
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels(g.index, rotation=30, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, out, name)


def _detection(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E04") & (df.metric.isin(["detected", "localized_correctly",
                                                          "detection_latency_slots"]))]
    if sub.empty:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, metric, title in zip(axes, ["detected", "detection_latency_slots"],
                                 ["Detection / localization rate", "Detection latency (slots)"]):
        g = sub[sub.metric == metric].groupby("scenario").value.mean()
        ax.bar(range(len(g)), g.values)
        ax.set_xticks(range(len(g)))
        ax.set_xticklabels(g.index, rotation=30, ha="right")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
        if metric == "detected":
            ax.set_ylim(0, 1.05)
    fig.suptitle("E04: diagnostics and self-healing")
    fig.tight_layout()
    return _save(fig, out, "fig_e04_detection")



def _e02_pareto(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E02") & (df.metric.isin(["mean_power_w", "sum_goodput_mbps"]))]
    if sub.empty:
        return []
    piv = sub.pivot_table(index=["scenario", "policy"], columns="metric",
                          values="value", aggfunc="mean").reset_index()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for policy, g in piv.groupby("policy"):
        ax.scatter(g.mean_power_w, g.sum_goodput_mbps, label=policy, s=42)
    for _, r in piv.iterrows():
        ax.annotate(str(r.scenario).replace("load", ""), (r.mean_power_w, r.sum_goodput_mbps),
                    fontsize=7, alpha=0.65)
    ax.set_xlabel("Mean power (W)")
    ax.set_ylabel("Sum goodput (Mbps)")
    ax.set_title("E02: QoS-energy Pareto view")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return _save(fig, out, "fig_e02_qos_energy_pareto")


def _e04_recovery(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E04") & (df.metric.isin(["detection_latency_slots",
                                                          "isolation_latency_slots"]))]
    fa = df[(df.experiment == "E04") & (df.metric == "false_alarm")]
    if sub.empty and fa.empty:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    if not sub.empty:
        for metric, label in (("detection_latency_slots", "detection"),
                              ("isolation_latency_slots", "isolation")):
            x = sub[sub.metric == metric].value.dropna().to_numpy()
            if x.size:
                axes[0].hist(x, bins=min(20, max(5, x.size)), alpha=0.6, label=label)
        axes[0].set_xlabel("Slots after fault onset")
        axes[0].set_ylabel("Count")
        axes[0].set_title("Detection / isolation latency")
        axes[0].legend()
        axes[0].grid(alpha=0.3)
    else:
        axes[0].text(0.5, 0.5, "no latency samples", ha="center")
    if not fa.empty:
        g = fa.groupby("scenario").value.mean()
        axes[1].bar(g.index, g.values, color="tab:red")
        axes[1].set_title("Healthy false alarms per run")
        axes[1].set_ylabel("Rate")
        axes[1].grid(axis="y", alpha=0.3)
    else:
        axes[1].text(0.5, 0.5, "no false-alarm samples", ha="center")
    fig.suptitle("E04: recovery and false-alarm evidence")
    fig.tight_layout()
    return _save(fig, out, "fig_e04_recovery")


def _security(df: pd.DataFrame, out: Path) -> list[str]:
    return _bar_by(df, "E05", "valid_executed", out, "fig_e05_security",
                   "E05: safe command execution", "Fraction", "security")


def _isac(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E06") & (df.metric.isin(["pd", "comm_overhead_pct",
                                                          "realized_sensing_fraction"]))]
    if sub.empty:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    s = sub[sub.metric == "pd"]
    for policy, g in s.groupby("policy"):
        m = g.groupby("scenario").value.mean()
        axes[0].plot(range(len(m)), m.values, marker="o", label=policy)
        axes[0].set_xticks(range(len(m)))
        axes[0].set_xticklabels(m.index, rotation=30, ha="right")
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].set_title("Detection probability")
    axes[0].set_ylabel("Pd")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    s = sub[sub.metric == "comm_overhead_pct"]
    for policy, g in s.groupby("policy"):
        m = g.groupby("scenario").value.mean()
        axes[1].plot(range(len(m)), m.values, marker="o", label=policy)
        axes[1].set_xticks(range(len(m)))
        axes[1].set_xticklabels(m.index, rotation=30, ha="right")
    axes[1].set_title("Realized communication overhead")
    axes[1].set_ylabel("%")
    axes[1].grid(alpha=0.3)
    fig.suptitle("E06: ISAC communication-sensing tradeoff")
    fig.tight_layout()
    return _save(fig, out, "fig_e06_isac")


def _ris(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E07") & (df.metric == "mean_sinr_db")]
    if sub.empty:
        return []
    fig, ax = plt.subplots(figsize=(8, 4))
    scenes = list(dict.fromkeys(sub.scenario))
    modes = list(dict.fromkeys(sub.policy))
    width = 0.8 / max(len(modes), 1)
    for i, mode in enumerate(modes):
        vals = [sub[(sub.scenario == s) & (sub.policy == mode)].value.mean() for s in scenes]
        ax.bar(np.arange(len(scenes)) + i * width, vals, width=width, label=mode)
    ax.set_xticks(np.arange(len(scenes)) + width * (len(modes) - 1) / 2)
    ax.set_xticklabels(scenes, rotation=20, ha="right")
    ax.set_ylabel("Mean SINR (dB)")
    ax.set_title("E07: RIS ablation (oracle labeled as unavailable upper bound)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, out, "fig_e07_ris")


def _fronthaul(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E08") & (df.metric.isin(["goodput_ratio", "loss_rate"]))]
    if sub.empty:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, metric, title in zip(axes, ["goodput_ratio", "loss_rate"],
                                 ["Goodput ratio vs baseline", "Observed loss rate"]):
        g = sub[sub.metric == metric].groupby("scenario").value.mean()
        ax.bar(range(len(g)), g.values)
        ax.set_xticks(range(len(g)))
        ax.set_xticklabels(g.index, rotation=30, ha="right")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("E08: fronthaul degradation")
    fig.tight_layout()
    return _save(fig, out, "fig_e08_fronthaul")


def _gpu(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E09") & (df.metric.isin(["tflops", "peak_vram_gb",
                                                          "context_build_s"]))]
    if sub.empty:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    s = sub[sub.metric == "tflops"]
    axes[0].bar(s.scenario, s.value, color="tab:blue")
    axes[0].set_title("GPU matmul throughput")
    axes[0].set_ylabel("TFLOP/s")
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].grid(axis="y", alpha=0.3)
    s = sub[sub.metric == "peak_vram_gb"]
    axes[1].bar(s.scenario, s.value, color="tab:orange")
    axes[1].set_title("Peak VRAM by UE count")
    axes[1].set_ylabel("GB")
    axes[1].tick_params(axis="x", rotation=30)
    axes[1].grid(axis="y", alpha=0.3)
    fig.suptitle("E09: GPU time and memory")
    fig.tight_layout()
    return _save(fig, out, "fig_e09_gpu")


def _integration(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "INTEGRATION") & (df.metric.str.contains("goodput_mbps"))]
    if sub.empty:
        return []
    fig, ax = plt.subplots(figsize=(7, 4))
    for seed, g in sub.groupby("seed"):
        order = ["pre_fault_goodput_mbps", "fault_goodput_mbps", "post_isolation_goodput_mbps"]
        vals = [g[g.metric == k].value.mean() for k in order]
        ax.plot(["pre", "fault window", "post isolation"], vals, marker="o", label=f"seed {seed}")
    ax.set_ylabel("Sum goodput (Mbps)")
    ax.set_title("INTEGRATION: closed-loop service impact")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return _save(fig, out, "fig_integration_recovery")


def _ocudu(df: pd.DataFrame, out: Path) -> list[str]:
    sub = df[(df.experiment == "E10") & (df.metric.isin(["pdsch_count", "pusch_crc_ok"]))]
    if sub.empty:
        return []
    fig, ax = plt.subplots(figsize=(6, 3.5))
    g = sub.groupby("metric").value.mean()
    ax.bar(g.index, g.values, color=["tab:green", "tab:red"][:len(g)])
    ax.set_ylabel("Scheduled / CRC-OK count")
    ax.set_title("E10: real OCUDU ru_dummy + test_mode")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, out, "fig_e10_ocudu")


def _assumptions(summary: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {
        "config_digest": summary.get("config_digest"),
        "suite": summary.get("suite"),
        "evidence_policy": {
            "SIMULATED": "abstract model output",
            "PHY_VALIDATED": "Sionna PHY/RT corroboration",
            "OCUDU_TESTED": "real OCUDU DU/PHY test-mode run",
            "HARDWARE_MEASURED": "never produced by this lab",
        },
        "claims": [
            "OCUDU test mode is not Open Fronthaul interoperability.",
            "Shannon/abstract rates are not measured 5G throughput.",
            "Timestamps at 4 ns resolution are not physical RF switching times.",
        ],
    }
    for name in ("radio", "energy", "power", "security"):
        path = CONFIG_DIR / f"{name}.yaml"
        if path.exists():
            try:
                data[name] = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                data[name] = {"parse_error": str(exc)}
    return data


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return "not-a-git-checkout"


def _low_load_saving(df: pd.DataFrame) -> float:
    x = df[(df.experiment == "E02") & (df.metric == "energy_saving_pct_vs_static")
           & (df.scenario.isin(["load0.05", "load0.10"]))]
    return float(x.value.mean()) if len(x) else float("nan")


def _low_load_saving_ci(df: pd.DataFrame) -> str:
    x = df[(df.experiment == "E02") & (df.metric == "energy_saving_pct_vs_static")
           & (df.scenario.isin(["load0.05", "load0.10"]))].value.to_numpy(float)
    if not len(x):
        return "n/a"
    mean, lo, hi = bootstrap_ci(x)
    return f"{mean:.3g} [{lo:.3g}, {hi:.3g}]"


def _low_load_delta(df: pd.DataFrame) -> float:
    x = df[(df.experiment == "E02") & (df.metric == "goodput_delta_mbps_vs_static")
           & (df.scenario.isin(["load0.05", "load0.10"]))]
    return float(x.value.mean()) if len(x) else float("nan")


def _low_load_delta_ci(df: pd.DataFrame) -> str:
    x = df[(df.experiment == "E02") & (df.metric == "goodput_delta_mbps_vs_static")
           & (df.scenario.isin(["load0.05", "load0.10"]))].value.to_numpy(float)
    if not len(x):
        return "n/a"
    mean, lo, hi = bootstrap_ci(x)
    return f"delta {mean:.3g} [{lo:.3g}, {hi:.3g}]"


def _low_load_p99_completed(df: pd.DataFrame) -> float:
    x = df[(df.experiment == "E02") & (df.policy == "predictive") &
           (df.metric == "latency_p99_completed_slots") &
           (df.scenario.isin(["load0.05", "load0.10"]))]
    return float(x.value.mean()) if len(x) else float("nan")


def _low_load_qos_delta(df: pd.DataFrame) -> float:
    x = df[(df.experiment == "E02") & (df.metric == "qos_expired_delta_vs_static")
           & (df.scenario.isin(["load0.05", "load0.10"]))]
    return float(x.value.mean()) if len(x) else float("nan")


def _low_load_qos_delta_ci(df: pd.DataFrame) -> str:
    x = df[(df.experiment == "E02") & (df.metric == "qos_expired_delta_vs_static")
           & (df.scenario.isin(["load0.05", "load0.10"]))].value.to_numpy(float)
    if not len(x):
        return "n/a"
    mean, lo, hi = bootstrap_ci(x)
    return f"delta {mean:.3g} [{lo:.3g}, {hi:.3g}]"


def _paired_ci(df: pd.DataFrame, exp: str, metric: str, sc_a: str, sc_b: str) -> str:
    a = df[(df.experiment == exp) & (df.metric == metric) & (df.scenario == sc_a)]
    b = df[(df.experiment == exp) & (df.metric == metric) & (df.scenario == sc_b)]
    if a.empty or b.empty:
        return "n/a"
    av = a.groupby("seed").value.mean()
    bv = b.groupby("seed").value.mean()
    common = av.index.intersection(bv.index)
    if len(common) == 0:
        return "n/a"
    out = paired_delta_ci(av.loc[common].to_numpy(), bv.loc[common].to_numpy())
    return f"delta {out['mean_delta']:.3g} [{out['ci_low']:.3g}, {out['ci_high']:.3g}] n={out['n']}"


def _evidence_rows(df: pd.DataFrame, summary: dict[str, Any]) -> list[dict[str, str]]:
    cmd = "docker compose run --rm sim python -m openru_x6.cli run-suite --suite {} --out results/{}".format(
        summary.get("suite", "full"), summary.get("suite", "full"))
    rows = [
        {"claim": "64-chain mode improves sum goodput over 8-chain mode at 128 UEs",
         "result": f"{_mean(df, 'E01', 'sum_goodput_mbps', scenario='chains64_ue128'):.1f} vs "
                   f"{_mean(df, 'E01', 'sum_goodput_mbps', scenario='chains8_ue128'):.1f} Mbps net",
         "test": "E01 paired seeds, PF, static energy",
         "ci": _paired_ci(df, "E01", "sum_goodput_mbps", "chains64_ue128", "chains8_ue128"),
         "limitation": "abstract channel + NR-grid resource accounting; not measured RF capacity",
         "command": cmd},
        {"claim": "Low-load predictive energy policy saves power versus static",
         "result": f"{_low_load_saving(df):.2f}% mean saving; goodput delta "
                   f"{_low_load_delta(df):+.1f} Mbps; deadline-expired delta "
                   f"{_low_load_qos_delta(df):+.3f} at load <= 0.1; "
                   f"P99 completed {_low_load_p99_completed(df):.1f} slots",
         "test": "E02", "ci": f"{_low_load_saving_ci(df)}; {_low_load_delta_ci(df)}; "
                               f"{_low_load_qos_delta_ci(df)}",
         "limitation": "thermal/energy model; savings are not QoS-neutral in this model; not board measurement",
         "command": cmd},
        {"claim": "Beamforming impairments reduce goodput",
         "result": f"{_mean(df, 'E03', 'sum_goodput_mbps', scenario='baseline'):.1f} Mbps baseline; "
                   f"{_mean(df, 'E03', 'sum_goodput_mbps', scenario='csi_delay'):.1f} Mbps with CSI delay",
         "test": "E03", "ci": _paired_ci(df, "E03", "sum_goodput_mbps", "baseline", "csi_delay"),
         "limitation": "modeled phase/delay impairments", "command": cmd},
        {"claim": "Statistical diagnostics detect and localize injected faults",
         "result": f"recall {_mean(df, 'E04', 'detected'):.2f}; localization "
                   f"{_mean(df, 'E04', 'localized_correctly'):.2f}; unrouted recovery actions "
                   f"{_mean(df, 'E04', 'recovery_actions_unrouted'):.2f}",
         "test": "E04", "ci": _ci(df, "E04", "detected"),
         "limitation": "injected simulation faults with seeded noisy telemetry; no board telemetry",
         "command": cmd},
        {"claim": "Safety kernel rejects unauthorized and unsafe commands",
         "result": f"unauthorized executed {_mean(df, 'E05', 'unauthorized_executed'):.2f}; "
                   f"unsafe sleep {_mean(df, 'E05', 'unsafe_sleep_applied'):.2f}",
         "test": "E05", "ci": _ci(df, "E05", "unauthorized_executed"),
         "limitation": "role-policy simulator only; no mTLS/credential identity or board secure element", "command": cmd},
        {"claim": "Adaptive ISAC sensing meets detection at bounded overhead",
         "result": f"episode Pd {_mean(df, 'E06', 'pd', policy='adaptive'):.2f}; "
                   f"per-look Pd {_mean(df, 'E06', 'pd_per_look', policy='adaptive'):.2f}; "
                   f"overhead {_mean(df, 'E06', 'comm_overhead_pct', policy='adaptive'):.2f}%",
         "test": "E06", "ci": _ci(df, "E06", "pd_per_look", policy="adaptive"),
         "limitation": "monostatic abstraction; episode and per-look metrics reported separately", "command": cmd},
        {"claim": "Practical RIS control improves blocked-link SINR over RIS-off",
         "result": f"{_mean(df, 'E07', 'gain_vs_off_db'):.2f} dB mean modeled gain",
         "test": "E07", "ci": _ci(df, "E07", "gain_vs_off_db"),
         "limitation": "geometry model; no fabricated RIS hardware", "command": cmd},
        {"claim": "Fronthaul loss/late traffic degrades service",
         "result": f"loss_5pct goodput ratio {_mean(df, 'E08', 'goodput_ratio', scenario='loss_5pct'):.3f}",
         "test": "E08", "ci": _ci(df, "E08", "goodput_ratio", scenario="loss_5pct"),
         "limitation": "packet-level abstraction", "command": cmd},
        {"claim": "GPU execution is feasible on the available device",
         "result": f"peak VRAM {_mean(df, 'E09', 'peak_vram_gb'):.2f} GB",
         "test": "E09", "ci": _ci(df, "E09", "peak_vram_gb"),
         "limitation": "single GPU run", "command": cmd},
        {"claim": "Real OCUDU reaches gNB start and test-mode PDSCH scheduling",
         "result": f"PDSCH count {_mean(df, 'E10', 'pdsch_count'):.0f}",
         "test": "E10 pinned OCUDU image, ru_dummy + test_mode",
         "ci": _ci(df, "E10", "pdsch_count"),
         "limitation": "DU/PHY only; not OFH interoperability or RF measurement",
         "command": cmd},
    ]
    present = set(df.experiment) if not df.empty else set()
    for row in rows:
        key = row["test"].split()[0].rstrip(":")
        if key not in present:
            row["result"] = "NOT_RUN (not in this suite)"
            row["ci"] = "n/a"
    return rows


def _md_table(rows: list[list[str]], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |")
    return "\n".join(out)


def _stage_status(exps: list[dict[str, Any]], excluded: str, include: bool = False) -> str:
    selected = [r for r in exps
                if (r.get("id") == excluded) == include]
    if not selected:
        return "NOT_RUN"
    if any(r.get("status") == "FAIL" for r in selected):
        return "FAIL"
    if all(r.get("status") == "PASS" for r in selected):
        return "PASS"
    return "PARTIAL"


def write_reports(out_dir: Path, summary: dict[str, Any], store: MetricsStore) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = _df(store)
    if df.empty and (out_dir / "metrics.csv").exists():
        df = pd.read_csv(out_dir / "metrics.csv")
    figures: list[str] = []
    for fn in (_goodput_vs_ue, _fairness, _energy, _e02_pareto, _detection, _e04_recovery,
               lambda d, o: _bar_by(d, "E03", "sum_goodput_mbps", o, "fig_e03_impairments",
                                    "E03: beamforming impairment impact", "Mbps"),
               _security, _isac, _ris, _fronthaul, _gpu, _integration, _ocudu):
        try:
            figures.extend(fn(df, out_dir))
        except Exception as exc:  # noqa: BLE001
            figures.extend(_placeholder(out_dir, f"fig_error_{fn.__name__}", str(exc)))
    assumptions = _assumptions(summary)
    (out_dir / "assumptions.yaml").write_text(
        yaml.safe_dump(assumptions, sort_keys=False), encoding="utf-8")
    image_id = None
    image_file = out_dir.parent / "image_id.txt"
    if image_file.exists():
        image_id = image_file.read_text(encoding="utf-8").strip().splitlines()[0]
    manifest = {
        "suite": summary.get("suite"),
        "config_digest": summary.get("config_digest"),
        "git_sha": _git_sha(),
        "image": os.environ.get("OPENRU_IMAGE_REF", "openru-x6-sim:0.1.0"),
        "image_id": image_id,
        "command": "docker compose run --rm sim python -m openru_x6.cli run-suite "
                   f"--suite {summary.get('suite')} --out results/{summary.get('suite')}",
        "python": platform.python_version(),
        "environment": summary.get("config_digest"),
        "artifacts": sorted(str(p.name) for p in out_dir.iterdir() if p.is_file()),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    exps = summary.get("experiments", [])
    exps = sorted(exps, key=lambda r: STATUS_ORDER.get(r.get("status", "ERROR"), 9))
    counts: dict[str, int] = {}
    for r in exps:
        counts[r.get("status", "ERROR")] = counts.get(r.get("status", "ERROR"), 0) + 1
    env = {}
    env_path = out_dir / "environment.json"
    if env_path.exists():
        env = json.loads(env_path.read_text(encoding="utf-8"))
    ev_rows = _evidence_rows(df, summary)
    status_rows = [[r.get("id", ""), r.get("title", ""), r.get("status", ""),
                    f"{r.get('runtime_s', 0):.1f}s", r.get("reason", "")] for r in exps]
    evidence_rows = [[r["claim"], r["result"], r["test"], r["ci"], r["limitation"],
                      f"`{r['command']}`"] for r in ev_rows]

    lines = [
        "# OpenRU-X6 simulation report",
        "",
        f"- Suite: **{summary.get('suite')}**",
        f"- Overall: **{summary.get('overall')}**",
        f"- Config digest: `{summary.get('config_digest')}`",
        f"- Runs: {counts.get('PASS', 0)} PASS, {counts.get('FAIL', 0)} FAIL, "
        f"{counts.get('BLOCKED', 0)} BLOCKED, {counts.get('NOT_RUN', 0)} NOT_RUN",
        f"- Runtime: {summary.get('runtime_s', 0):.1f}s; metric rows: {summary.get('n_metric_rows', len(df))}",
        f"- Generated (UTC): {summary.get('finished_utc')}",
        f"- Simulator regression (E00-E09): **{_stage_status(exps, 'E10')}**",
        f"- OCUDU DU/PHY test mode: **{_stage_status(exps, 'E10', include=True)}**",
        "- O-RAN OFH / RU emulation / physical RU readiness: **BLOCKED / NOT_TESTED**",
        "",
        "## Executive conclusions",
        "",
    ]
    exec_rows = [r for r in ev_rows if "nan" not in r["result"].lower()
                 and "not_run" not in r["result"].lower()][:8]
    for r in exec_rows:
        lines.append(f"- **{r['claim']}**: {r['result']} ({r['test']}; CI {r['ci']}). "
                     f"*Limitation:* {r['limitation']}.")
    lines += [
        "",
        "All quantitative statements above are generated from `metrics.csv`/`summary.json`. "
        "No hardware measurement is claimed. The OCUDU result is DU/PHY test-mode evidence, "
        "not Open Fronthaul interoperability and not system-level RU readiness.",
        "",
        "## What ran",
        "",
        _md_table(status_rows, ["ID", "Title", "Status", "Runtime", "Reason"]),
        "",
        "## Environment and provenance",
        "",
        f"- Python: {env.get('python', platform.python_version())}",
        f"- GPU: {(env.get('gpu_selected') or {}).get('name', 'n/a')}",
        f"- CUDA: {(env.get('gpu_selected') or {}).get('cuda_version', 'n/a')}",
        f"- Git: `{manifest['git_sha']}`",
        f"- Image: `{manifest['image']}` (id `{manifest.get('image_id') or 'n/a'}`)",
        f"- Command: `{manifest['command']}`",
        "",
        "## Evidence table",
        "",
        _md_table(evidence_rows, ["Claim", "Result", "Test / config", "Observed 95% CI",
                                  "Limitation", "Reproducibility command"]),
        "",
        "## Figures",
        "",
    ]
    for fig in figures:
        if fig.endswith(".png"):
            lines.append(f"![{fig}]({fig})")
    lines += [
        "",
        "## Unsupported or blocked claims",
        "",
        "- RF hardware feasibility, PCB signal integrity, thermal feasibility and antenna "
        "calibration are **not measured** by this lab.",
        "- Open Fronthaul interoperability with OCUDU is **NOT_TESTED**; only "
        "`ru_dummy` + `test_mode` DU/PHY scheduling is exercised. E10 PASS therefore does "
        "not establish O-RAN system integration or RU hardware readiness.",
        "- `ru_emu` is **BLOCKED** because the pinned OCUDU nightly image does not contain "
        "an `ru_emu` binary.",
        "- RIS and ISAC results are model outputs; the RIS oracle is an unavailable upper bound.",
        "",
        "## Architecture and PCB feature recommendations",
        "",
        "1. Preserve the 64T64R/256-feed datapath as the reference, but make tile-level power "
        "gating and RF-chain fallback first-class so low load can use fewer active tiles.",
        "2. Require per-tile telemetry: PA current/gain, VSWR, phase error, board temperature, "
        "fan state, supply voltage, PTP offset, and per-tile enable/readback.",
        "3. Put the safety kernel and audit log on a separate control path; never allow sleep "
        "of the sole coverage cell.",
        "4. Validate the first physical tile at 4T4R/16 feeds before committing the full array: "
        "the simulation supports the architecture but cannot prove RF/PCB feasibility.",
        "5. Add hardware-in-the-loop hooks for real OFH and RU emulation; keep OCUDU test-mode "
        "evidence labeled separately from interoperability.",
        "",
        "## Risks and prioritized next experiments",
        "",
        "- **P0:** Full multi-seed suite with >=20 paired seeds; verify confidence-interval "
        "width and preserve failed runs.",
        "- **P0:** Hardware-backed PA/VSWR/thermal measurements on a single tile.",
        "- **P1:** Real OFH/RU-emulation integration; current E10 is DU/PHY only.",
        "- **P1:** RIS/ISAC validation with measured phase/quantization and control latency.",
        "- **P2:** 32T32R vs 64T64R Pareto sweep and PCB cost/power trade study.",
        "",
        "## Reproducibility and resources",
        "",
        f"```bash\n{manifest['command']}\n```",
        "",
        "Requires Docker with NVIDIA GPU access to physical GPU 1 (exposed as `cuda:0` in the "
        "container), the pinned `sionna:2.2.0` base image, and the OCUDU nightly image for E10. "
        "The container needs `/var/run/docker.sock` and Docker group access only for E10.",
    ]
    md = "\n".join(lines) + "\n"
    (out_dir / "report.md").write_text(md, encoding="utf-8")

    img_html = []
    for fig in figures:
        if not fig.endswith(".png"):
            continue
        b64 = base64.b64encode((out_dir / fig).read_bytes()).decode("ascii")
        img_html.append(f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(fig)}">'
                        f'<figcaption>{html.escape(fig)}</figcaption></figure>')

    def table(rows: list[list[str]], header: list[str]) -> str:
        head = "".join(f"<th>{html.escape(h)}</th>" for h in header)
        body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>"
                       for row in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    exec_rows = [r for r in ev_rows if "nan" not in r["result"].lower()
                 and "not_run" not in r["result"].lower()][:8]
    exec_items = "".join(
        f"<li><b>{html.escape(r['claim'])}</b>: {html.escape(r['result'])} "
        f"({html.escape(r['test'])}; CI {html.escape(r['ci'])}). "
        f"<i>Limitation:</i> {html.escape(r['limitation'])}.</li>" for r in exec_rows)
    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>OpenRU-X6 simulation report</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1180px;margin:2rem auto;padding:0 1rem;color:#17202a;line-height:1.45}}
h1,h2{{color:#0b3d5c}} table{{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.9rem}}
th,td{{border:1px solid #c9d3dc;padding:.4rem .5rem;text-align:left;vertical-align:top}}
th{{background:#eaf2f8}} code{{background:#f2f4f5;padding:.1rem .3rem;border-radius:3px}}
figure{{margin:1.2rem 0}} img{{max-width:100%;border:1px solid #d5dde3}}
figcaption{{color:#556;font-size:.85rem}} .warn{{background:#fff4e5;border-left:4px solid #d68910;padding:.7rem 1rem}}
</style></head><body>
<h1>OpenRU-X6 simulation report</h1>
<p><b>Suite:</b> {html.escape(str(summary.get('suite')))} &nbsp; <b>Overall:</b>
{html.escape(str(summary.get('overall')))} &nbsp; <b>Config digest:</b>
<code>{html.escape(str(summary.get('config_digest')))}</code></p>
<p><b>Simulator regression (E00-E09):</b> {html.escape(_stage_status(exps, 'E10'))} &nbsp;
<b>OCUDU DU/PHY test mode:</b> {html.escape(_stage_status(exps, 'E10', include=True))} &nbsp;
<b>O-RAN OFH / RU readiness:</b> BLOCKED / NOT_TESTED</p>
<p>{counts.get('PASS', 0)} PASS, {counts.get('FAIL', 0)} FAIL,
{counts.get('BLOCKED', 0)} BLOCKED, {counts.get('NOT_RUN', 0)} NOT_RUN;
runtime {summary.get('runtime_s', 0):.1f}s; {summary.get('n_metric_rows', len(df))} metric rows.</p>
<h2>Executive conclusions</h2><ul>{exec_items}</ul>
<p class="warn">No HARDWARE_MEASURED evidence is produced. OCUDU test-mode evidence is not
Open Fronthaul interoperability and not an RF measurement.</p>
<h2>What ran</h2>{table(status_rows, ["ID", "Title", "Status", "Runtime", "Reason"])}
<h2>Evidence table</h2>{table(evidence_rows, ["Claim", "Result", "Test / config", "95% CI", "Limitation", "Reproducibility command"])}
<h2>Figures</h2>{''.join(img_html)}
<h2>Unsupported or blocked claims</h2>
<ul><li>RF/PCB/thermal/antenna feasibility is not measured.</li>
<li>Open Fronthaul interoperability with OCUDU is NOT_TESTED; E10 PASS is DU/PHY test mode only.</li>
<li><code>ru_emu</code> is BLOCKED in the pinned image.</li>
<li>RIS oracle is an unavailable upper bound; ISAC/RIS are model outputs.</li></ul>
<h2>Reproducibility and resources</h2>
<p><code>{html.escape(manifest['command'])}</code></p>
<p>Requires Docker, NVIDIA GPU 1 (inside container <code>cuda:0</code>), the pinned
<code>sionna:2.2.0</code> base image and the OCUDU nightly image for E10. Docker socket access
is needed only for E10.</p>
</body></html>"""
    (out_dir / "report.html").write_text(html_doc, encoding="utf-8")
    return figures + ["report.md", "report.html", "assumptions.yaml", "manifest.json"]
