from __future__ import annotations

from openru_x6.rfcal.observability import (
    DEFAULT_ARCHITECTURES,
    FACTORY_VNA_FEED_TABLE,
    H2_AVAILABLE,
    IDEAL_16IQ,
    NEAR_FIELD_PROBE,
    PROPOSED_SWITCHED_FEED_LOOPBACK,
    audit_h2_observability,
    get_architecture,
    identifiability_summary,
)
from openru_x6.rfcal.topology import load_topology


def test_h2_available_architecture_only_observes_chain_phase_and_feed_power() -> None:
    topology = load_topology()
    summary = identifiability_summary(topology, H2_AVAILABLE)
    assert summary["chain_relative_complex_response"] is True
    assert summary["feed_amplitude"] is True
    assert summary["feed_phase"] is False
    assert summary["per_feed_complex_response"] is False
    assert summary["observable_complex_chain_responses"] == 4
    assert summary["observable_feed_power_measurements"] == 16
    assert summary["observable_feed_complex_responses"] == 0
    assert summary["unidentifiable"] == ["feed phase for all 16 feeds"]


def test_per_feed_complex_architectures_observe_feed_phase() -> None:
    topology = load_topology()
    for architecture in (
        FACTORY_VNA_FEED_TABLE,
        NEAR_FIELD_PROBE,
        PROPOSED_SWITCHED_FEED_LOOPBACK,
        IDEAL_16IQ,
    ):
        summary = identifiability_summary(topology, architecture)
        assert summary["feed_phase"] is True
        assert summary["observable_feed_complex_responses"] == 16
        assert summary["unidentifiable"] == []
    assert H2_AVAILABLE.realizable_on_current_h2 is True
    assert H2_AVAILABLE.requires_hardware_change is False
    assert PROPOSED_SWITCHED_FEED_LOOPBACK.realizable_on_current_h2 is False
    assert PROPOSED_SWITCHED_FEED_LOOPBACK.requires_hardware_change is True
    assert NEAR_FIELD_PROBE.requires_external_fixture is True


def test_unknown_architecture_is_rejected() -> None:
    try:
        get_architecture("not-a-real-architecture")
    except ValueError as error:
        assert "unknown calibration architecture" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_h2_audit_cites_schematic_evidence_and_conclusion() -> None:
    topology = load_topology()
    audit = audit_h2_observability(topology)
    assert audit["evidence_label"] == "SCHEMATIC_AUDIT"
    assert audit["hardware_measured"] is False
    assert audit["identifiability"]["feed_phase"] is False
    assert "cannot identify 16 independent feed complex responses" in audit["conclusion"]
    claims = {finding["claim"] for finding in audit["findings"]}
    assert "The per-element detectors are power-only." in claims
    assert "The H2 tile does not provide per-feed complex IQ." in claims
    assert set(audit["supported_architectures"]) == set(DEFAULT_ARCHITECTURES)
