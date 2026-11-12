"""Array topology and feed-map handling for the OpenRU-X6 RF calibration model.

The default topology mirrors ``hardware/H1_FEED_POLARIZATION_MAP.csv``: four
RF chains, sixteen feeds, and eight dual-polarized sites in a 2x4 grid.  The
module is deliberately independent of the hardware control path.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

SPEED_OF_LIGHT_MPS = 299_792_458.0
DEFAULT_CARRIER_HZ = 8.4e9
DEFAULT_SITE_PITCH_M = SPEED_OF_LIGHT_MPS / DEFAULT_CARRIER_HZ / 2.0
DEFAULT_POLARIZATIONS = ("V", "H")


@dataclass(frozen=True)
class Site:
    """A dual-polarized radiating site."""

    index: int
    row: int
    col: int
    y_m: float
    z_m: float


@dataclass(frozen=True)
class Feed:
    """A single polarization port belonging to one site and RF chain."""

    index: int
    chain: int
    site: int
    polarization: str
    y_m: float
    z_m: float


@dataclass(frozen=True)
class Topology:
    """Array geometry plus feed-to-chain ownership."""

    name: str
    carrier_freq_hz: float
    sites: tuple[Site, ...]
    feeds: tuple[Feed, ...]
    source: str = "embedded H1 4T4R topology"

    @property
    def wavelength_m(self) -> float:
        return SPEED_OF_LIGHT_MPS / self.carrier_freq_hz

    @property
    def wavenumber_rad_m(self) -> float:
        return 2.0 * np.pi / self.wavelength_m

    @property
    def n_sites(self) -> int:
        return len(self.sites)

    @property
    def n_feeds(self) -> int:
        return len(self.feeds)

    @property
    def n_chains(self) -> int:
        return len({feed.chain for feed in self.feeds})

    @property
    def chain_ids(self) -> tuple[int, ...]:
        return tuple(sorted({feed.chain for feed in self.feeds}))

    @property
    def polarization_names(self) -> tuple[str, ...]:
        return tuple(sorted({feed.polarization for feed in self.feeds}))

    def positions_m(self) -> np.ndarray:
        """Return feed positions as an ``(n_feeds, 3)`` array in metres."""
        return np.asarray([(0.0, feed.y_m, feed.z_m) for feed in self.feeds], dtype=float)

    def feed(self, index: int) -> Feed:
        return self.feeds[index]

    def site(self, index: int) -> Site:
        return self.sites[index]

    def feeds_for_chain(self, chain: int) -> tuple[Feed, ...]:
        return tuple(feed for feed in self.feeds if feed.chain == chain)

    def chain_indices(self, chain: int) -> np.ndarray:
        return np.asarray(
            [feed.index for feed in self.feeds if feed.chain == chain], dtype=int
        )

    def validate(self) -> None:
        if not self.name:
            raise ValueError("topology name must not be empty")
        if not np.isfinite(self.carrier_freq_hz) or self.carrier_freq_hz <= 0:
            raise ValueError("carrier_freq_hz must be finite and positive")
        if not self.sites:
            raise ValueError("topology must contain at least one site")
        if not self.feeds:
            raise ValueError("topology must contain at least one feed")
        if len({site.index for site in self.sites}) != len(self.sites):
            raise ValueError("site indices must be unique")
        if len({feed.index for feed in self.feeds}) != len(self.feeds):
            raise ValueError("feed indices must be unique")
        site_indices = {site.index for site in self.sites}
        for site in self.sites:
            if not (np.isfinite(site.y_m) and np.isfinite(site.z_m)):
                raise ValueError(f"site {site.index} has non-finite coordinates")
        for feed in self.feeds:
            if feed.site not in site_indices:
                raise ValueError(f"feed {feed.index} references missing site {feed.site}")
            if not feed.polarization:
                raise ValueError(f"feed {feed.index} has an empty polarization label")
            if not (np.isfinite(feed.y_m) and np.isfinite(feed.z_m)):
                raise ValueError(f"feed {feed.index} has non-finite coordinates")
        if sorted({feed.index for feed in self.feeds}) != list(range(self.n_feeds)):
            raise ValueError("feed indices must be contiguous from zero")

    def is_4t4r(self) -> bool:
        return self.n_chains == 4 and self.n_feeds == 16 and self.n_sites == 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "name": self.name,
            "carrier_freq_hz": self.carrier_freq_hz,
            "source": self.source,
            "sites": [asdict(site) for site in self.sites],
            "feeds": [asdict(feed) for feed in self.feeds],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Topology":
        topology = cls(
            name=str(data["name"]),
            carrier_freq_hz=float(data["carrier_freq_hz"]),
            sites=tuple(
                sorted((Site(**item) for item in data["sites"]), key=lambda site: site.index)
            ),
            feeds=tuple(
                sorted((Feed(**item) for item in data["feeds"]), key=lambda feed: feed.index)
            ),
            source=str(data.get("source", "JSON topology")),
        )
        topology.validate()
        return topology

    def to_json(self, path: str | Path) -> None:
        write_json(path, self.to_dict())

    @classmethod
    def from_json(cls, path: str | Path) -> "Topology":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "feed_index",
                    "sim_chain",
                    "local_site",
                    "site_row",
                    "site_col",
                    "polarization",
                    "y_mm",
                    "z_mm",
                    "y_m",
                    "z_m",
                ],
            )
            writer.writeheader()
            for feed in self.feeds:
                site = self.site(feed.site)
                writer.writerow(
                    {
                        "feed_index": feed.index,
                        "sim_chain": feed.chain,
                        "local_site": feed.site,
                        "site_row": site.row,
                        "site_col": site.col,
                        "polarization": feed.polarization,
                        "y_mm": feed.y_m * 1000.0,
                        "z_mm": feed.z_m * 1000.0,
                        "y_m": feed.y_m,
                        "z_m": feed.z_m,
                    }
                )

    @classmethod
    def from_feed_map_csv(cls, path: str | Path) -> "Topology":
        path = Path(path)
        rows = _read_feed_map_rows(path)
        if not rows:
            raise ValueError(f"feed map {path} is empty")

        sites_by_index: dict[int, Site] = {}
        feeds: list[Feed] = []
        for feed_index, row in enumerate(rows):
            site_index = int(row["local_site"])
            y_m = float(row["y_mm"]) / 1000.0
            z_m = float(row["z_mm"]) / 1000.0
            site = Site(
                index=site_index,
                row=int(row.get("site_row", 0)),
                col=int(row.get("site_col", 0)),
                y_m=y_m,
                z_m=z_m,
            )
            previous = sites_by_index.get(site_index)
            if previous is None:
                sites_by_index[site_index] = site
            elif not _same_site(previous, site):
                raise ValueError(f"inconsistent geometry for site {site_index}")
            feeds.append(
                Feed(
                    index=feed_index,
                    chain=int(row["sim_chain"]),
                    site=site_index,
                    polarization=str(row["polarization"]).strip().upper(),
                    y_m=y_m,
                    z_m=z_m,
                )
            )

        topology = cls(
            name="openru-x6-h1-4t4r-from-feed-map",
            carrier_freq_hz=DEFAULT_CARRIER_HZ,
            sites=tuple(sites_by_index[index] for index in sorted(sites_by_index)),
            feeds=tuple(feeds),
            source=str(path),
        )
        topology.validate()
        return topology

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Topology":
        if path is None:
            return cls.default_4t4r()
        path = Path(path)
        if path.suffix.lower() == ".json":
            return cls.from_json(path)
        if path.suffix.lower() == ".csv":
            return cls.from_feed_map_csv(path)
        raise ValueError(f"unsupported topology format: {path.suffix}")

    @classmethod
    def default_4t4r(cls) -> "Topology":
        pitch = DEFAULT_SITE_PITCH_M
        sites: list[Site] = []
        feeds: list[Feed] = []
        for row in range(2):
            z_m = (row - 0.5) * pitch
            for col in range(4):
                site_index = row * 4 + col
                y_m = (col - 1.5) * pitch
                sites.append(Site(index=site_index, row=row, col=col, y_m=y_m, z_m=z_m))
                chain = row * 2 + col // 2
                for polarization in DEFAULT_POLARIZATIONS:
                    feeds.append(
                        Feed(
                            index=len(feeds),
                            chain=chain,
                            site=site_index,
                            polarization=polarization,
                            y_m=y_m,
                            z_m=z_m,
                        )
                    )
        topology = cls(
            name="openru-x6-h1-4t4r",
            carrier_freq_hz=DEFAULT_CARRIER_HZ,
            sites=tuple(sites),
            feeds=tuple(feeds),
            source="H1 documented 4T4R topology",
        )
        topology.validate()
        return topology


def _read_feed_map_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"sim_chain", "local_site", "polarization", "y_mm", "z_mm"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = required.difference(reader.fieldnames or [])
            raise ValueError(f"feed map is missing columns: {sorted(missing)}")
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def _same_site(left: Site, right: Site) -> bool:
    return (
        left.row == right.row
        and left.col == right.col
        and np.isclose(left.y_m, right.y_m, atol=1e-9)
        and np.isclose(left.z_m, right.z_m, atol=1e-9)
    )


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load_topology(path: str | Path | None = None) -> Topology:
    return Topology.load(path)


def chain_groups(topology: Topology) -> dict[int, tuple[Feed, ...]]:
    return {chain: topology.feeds_for_chain(chain) for chain in topology.chain_ids}


def feed_indices_by_polarization(topology: Topology) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for polarization in topology.polarization_names:
        result[polarization] = np.asarray(
            [feed.index for feed in topology.feeds if feed.polarization == polarization],
            dtype=int,
        )
    return result


def iter_feeds(topology: Topology) -> Iterable[Feed]:
    return iter(topology.feeds)
