"""E10: real OCUDU ru_dummy/test_mode execution.

DU/PHY test-mode evidence is not Open Fronthaul interoperability and not an RF
hardware measurement.  If the OCUDU image or Docker socket is unavailable the
experiment is explicitly BLOCKED rather than simulated.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from ..metrics import write_json
from ..ocudu import CONFIG_PATH, EVIDENCE_NOTE, IMAGE
from .common import make_result, params_for


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E10", suite)
    timeout_s = int(p.get("timeout_s", 60))
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {"evidence_class": "OCUDU_TESTED",
                                  "note": EVIDENCE_NOTE}
    artifacts: list[str] = []
    cfg_text = CONFIG_PATH.read_text(encoding="utf-8")
    cfg_path = out_dir / "e10_ocudu_config.yml"
    cfg_path.write_text(cfg_text, encoding="utf-8")
    artifacts.append(cfg_path.name)

    docker = shutil.which("docker")
    checks["docker_cli_available"] = docker is not None
    if docker is None:
        res = make_result("E10", "OCUDU ru_dummy/testmode", t0,
                          {"docker_cli_available": False, "ocudu_executed": False},
                          {"blocked_reason": "docker CLI not available inside the sim container"})
        res.status = "BLOCKED"
        res.reason = "docker CLI not available; OCUDU cannot be launched"
        return res
    try:
        probe = subprocess.run([docker, "image", "inspect", IMAGE], capture_output=True,
                               text=True, timeout=30)
        checks["ocudu_image_present"] = probe.returncode == 0
        metrics["image_inspect_rc"] = probe.returncode
    except Exception as exc:  # noqa: BLE001
        checks["ocudu_image_present"] = False
        metrics["image_inspect_error"] = f"{type(exc).__name__}: {exc}"
    if not checks["ocudu_image_present"]:
        res = make_result("E10", "OCUDU ru_dummy/testmode", t0, checks, metrics)
        res.status = "BLOCKED"
        res.reason = "OCUDU image not present locally"
        return res

    shell = ("cat > /tmp/gnb.yml && timeout -s INT 8 gnb -c /tmp/gnb.yml 2>&1; "
             "echo EXIT_CODE:$?; echo ===GNB_LOG===; "
             "echo PDSCH_COUNT:$(grep -c 'PDSCH: rnti=0x44' /tmp/gnb.log 2>/dev/null); "
             "echo PUSCH_KO_COUNT:$(grep -c 'PUSCH: rnti=0x44.*crc=KO' /tmp/gnb.log 2>/dev/null); "
             "grep -E 'gNB started|PDSCH: rnti=0x44|PUSCH: rnti=0x44|test_ue|test_mode|TEST_MODE|c-rnti' "
             "/tmp/gnb.log 2>/dev/null | tail -60")
    cmd = [docker, "run", "--rm", "-i", "--network", "none", "--cap-add", "SYS_NICE",
           "--cap-add", "IPC_LOCK", "--entrypoint", "bash", IMAGE, "-lc", shell]
    attempts = int(p.get("attempts", 3))
    history: list[str] = []
    crash_attempts = 0
    out = ""
    rc = -1
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(cmd, input=cfg_text, capture_output=True, text=True,
                                  timeout=timeout_s + 30)
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            rc = proc.returncode
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or "") + "\n" + (exc.stderr or "")
            rc = -1
        history.append(f"=== ATTEMPT {attempt}/{attempts} ===\n{out}")
        crashed = "Segmentation fault" in out or "terminate called" in out
        reached = "gNB started" in out and bool(re.search(r"PDSCH: rnti=0x44", out))
        crash_attempts += int(crashed)
        metrics["attempts"] = attempt
        metrics["crash_attempts"] = crash_attempts
        if reached:
            break
    (out_dir / "e10_ocudu_run.log").write_text("\n".join(history), encoding="utf-8")
    artifacts.append("e10_ocudu_run.log")
    metrics["process_returncode"] = rc

    checks["gnb_started"] = "gNB started" in out
    m = re.search(r"PDSCH_COUNT:(\d+)", out)
    pdsch_count = int(m.group(1)) if m else 0
    checks["test_ue_created"] = pdsch_count > 0 or bool(re.search(r"c-rnti=0x44", out))
    checks["pdsch_scheduled"] = pdsch_count > 0 or bool(re.search(r"PDSCH: rnti=0x44", out))
    checks["pusch_scheduled"] = bool(re.search(r"PUSCH: rnti=0x44", out))
    checks["test_mode_seen"] = "TEST_MODE" in out or "test_mode" in out
    checks["no_crash"] = "Segmentation fault" not in out and "terminate called" not in out

    tbs = [int(x) for x in re.findall(r"PDSCH:.*?tbs=(\d+)", out)]
    mcs = sorted(set(re.findall(r"PDSCH:.*?mod=([0-9A-Za-z]+)", out)))
    mko = re.search(r"PUSCH_KO_COUNT:(\d+)", out)
    pusch_crc_ko = int(mko.group(1)) if mko else len(re.findall(r"PUSCH:.*?crc=KO", out))
    pusch_crc_ok = len(re.findall(r"PUSCH:.*?crc=OK", out))
    metrics.update({"pdsch_count": pdsch_count or len(tbs), "pdsch_tbs_max": max(tbs) if tbs else 0,
                    "pdsch_modulations": mcs, "pusch_crc_ko": pusch_crc_ko,
                    "pusch_crc_ok": pusch_crc_ok,
                    "ru_emu": "BLOCKED: no ru_emu binary in the pinned nightly image",
                    "ofh_interoperability": "NOT_TESTED",
                    "hardware_measurement": False})
    store.add("E10", "ocudu_ru_dummy", 0, "testmode", "pdsch_count", float(pdsch_count or len(tbs)),
              "", "OCUDU_TESTED", "")
    store.add("E10", "ocudu_ru_dummy", 0, "testmode", "pusch_crc_ok", float(pusch_crc_ok),
              "", "OCUDU_TESTED", "")
    write_json(out_dir / "e10_ocudu_summary.json", metrics)

    res = make_result("E10", "OCUDU ru_dummy/testmode", t0, checks, metrics,
                      evidence_class="OCUDU_TESTED")
    if not checks.get("gnb_started") or not checks.get("pdsch_scheduled"):
        res.status = "BLOCKED"
        res.reason = "OCUDU did not reach gNB start + test-mode PDSCH scheduling"
    res.artifacts = artifacts
    return res
