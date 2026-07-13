"""Tests for offline mode: save parsing and the upload endpoint."""

from __future__ import annotations

import struct
import zlib
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.offline.save_parser import SaveParseError, decompress_body, parse_save


def _fstring(value: str) -> bytes:
    """Encode a UTF-8 Unreal ``FString`` (length includes the null terminator)."""
    raw = value.encode("utf-8") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def _ticks(dt: datetime) -> int:
    return (dt - datetime(1, 1, 1, tzinfo=UTC)) // timedelta(microseconds=1) * 10


def make_save(
    *,
    session: str = "Test Session",
    map_name: str = "Persistent_Level",
    build: int = 368883,
    duration: int = 3600,
    instances: dict[str, int] | None = None,
) -> bytes:
    """Build a minimal but structurally valid ``.sav``: real header + zlib body."""
    header = struct.pack("<iii", 13, 46, build)  # header/save/build version
    header += _fstring(map_name)
    header += _fstring("?startloc=Grass Fields")  # map options
    header += _fstring(session)
    header += struct.pack("<i", duration)
    header += struct.pack("<q", _ticks(datetime(2026, 7, 1, 12, 0, tzinfo=UTC)))
    header += struct.pack("<b", 1)  # session visibility

    counts = instances or {"Build_ConstructorMk1_C": 2, "Build_GeneratorCoal_C": 1}
    body_parts: list[bytes] = []
    instance_id = 2147470000
    for cls, count in counts.items():
        for _ in range(count):
            body_parts.append(f"{cls}_{instance_id}".encode("ascii"))
            instance_id += 1
    body = b"\x00PAD\x00".join(body_parts)
    return header + zlib.compress(body)


def test_parse_header_fields() -> None:
    parsed = parse_save(make_save(session="Northern Forest", duration=7200))
    assert parsed.header.session_name == "Northern Forest"
    assert parsed.header.map_name == "Persistent_Level"
    assert parsed.header.play_duration_seconds == 7200
    assert parsed.header.saved_at == datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def test_building_counts_dedupe_instances() -> None:
    save = make_save(
        instances={"Build_ConstructorMk1_C": 3, "Build_AssemblerMk1_C": 1}
    )
    parsed = parse_save(save)
    assert parsed.building_counts["Build_ConstructorMk1_C"] == 3
    assert parsed.building_counts["Build_AssemblerMk1_C"] == 1


def test_parse_rejects_non_save() -> None:
    with pytest.raises(SaveParseError):
        parse_save(b"not a satisfactory save at all, just text")


def test_decompress_body_handles_no_streams() -> None:
    assert decompress_body(b"\x00\x01\x02\x03") == b""


async def test_upload_and_clear_save(client: AsyncClient) -> None:
    # Baseline: simulation source, no save loaded.
    status = (await client.get("/api/v1/offline/status")).json()
    assert status["active"] is False
    assert status["source"] == "simulation"

    save = make_save(
        session="Endgame Base",
        instances={
            "Build_ConstructorMk1_C": 4,
            "Build_AssemblerMk1_C": 2,
            "Build_MinerMk2_C": 3,
            "Build_GeneratorCoal_C": 8,
        },
    )
    resp = await client.post(
        "/api/v1/offline/save",
        files={"file": ("factory.sav", save, "application/octet-stream")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["source"] == "save"
    summary = body["save"]
    assert summary["session_name"] == "Endgame Base"
    assert summary["machine_count"] == 4 + 2 + 3  # production + extraction
    assert summary["generator_count"] == 8
    # 8 coal generators * 75 MW nominal capacity.
    assert summary["estimated_power_capacity_mw"] == pytest.approx(600.0)

    # The dashboard now reflects the save.
    dash = (await client.get("/api/v1/dashboard")).json()
    assert dash["source"] == "save"
    assert dash["machines"]["total"] == 9

    # Clearing restores the simulation source.
    cleared = (await client.delete("/api/v1/offline/save")).json()
    assert cleared["active"] is False
    assert cleared["source"] == "simulation"
    dash = (await client.get("/api/v1/dashboard")).json()
    assert dash["source"] == "simulation"


async def test_upload_empty_file_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/offline/save",
        files={"file": ("empty.sav", b"", "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_failed"
