"""H1 topology A must stay identical to the simulated tile-0 feed ownership."""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "hardware" / "H1_FEED_POLARIZATION_MAP.csv"


def test_h1_feed_map_matches_simulation(feed_map):
    rows = list(csv.DictReader(CSV.open()))
    assert len(rows) == 16
    for r in rows:
        f = int(r["sim_feed_index"])
        assert int(feed_map.feed_tile[f]) == 0
        assert int(feed_map.feed_chain[f]) == int(r["sim_chain"])
        assert ("V", "H")[int(feed_map.feed_pol[f])] == r["polarization"]
        assert r["adar1000_ref"] == f"U_BF{int(r['sim_chain']) + 1}"  # one BFIC per RF chain
    assert {r["front_end_ref"] for r in rows} == {f"U_FE{i}" for i in range(1, 17)}
    assert len({(r["sim_chain"], r["adar1000_channel"]) for r in rows}) == 16
