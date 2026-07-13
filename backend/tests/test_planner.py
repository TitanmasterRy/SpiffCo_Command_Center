"""Tests for the factory planner: validation, summary, CRUD, versioning."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.planner.geometry import Rect, footprint_cells, placement_rect
from app.planner.service import summarize, validate_layout
from app.schemas.planner import Footprint, GridSpec, Layout, Placement


def _layout(*placements: Placement, width: int = 40, length: int = 40) -> Layout:
    grid = GridSpec(width=width, length=length, cell_cm=100)
    return Layout(grid=grid, placements=list(placements))


def test_footprint_cells_and_rotation() -> None:
    fp = Footprint(width=6, length=9)
    assert footprint_cells(fp, 100) == (6, 9)
    # 50 cm cells => twice the cell count.
    assert footprint_cells(fp, 50) == (12, 18)
    rot = placement_rect(Placement(id="a", building="smelter", x=0, y=0, rotation=90), fp, 100)
    assert (rot.width, rot.length) == (9, 6)


def test_rect_overlap_and_bounds() -> None:
    grid = GridSpec(width=10, length=10, cell_cm=100)
    assert Rect(0, 0, 5, 5).overlaps(Rect(4, 4, 3, 3))
    assert not Rect(0, 0, 4, 4).overlaps(Rect(4, 0, 4, 4))  # touching edges is fine
    assert Rect(0, 0, 10, 10).within(grid)
    assert not Rect(6, 6, 6, 6).within(grid)


def test_validate_layout_accepts_non_overlapping() -> None:
    validate_layout(
        _layout(
            Placement(id="a", building="smelter", x=0, y=0),
            Placement(id="b", building="smelter", x=10, y=0),
        )
    )


def test_validate_layout_reports_overlap_and_oob() -> None:
    from app.errors import ValidationFailedError

    with pytest.raises(ValidationFailedError) as exc:
        validate_layout(
            _layout(
                Placement(id="a", building="smelter", x=0, y=0),
                Placement(id="b", building="smelter", x=2, y=2),  # overlaps a
                Placement(id="c", building="smelter", x=38, y=38),  # off grid
                Placement(id="d", building="does-not-exist", x=20, y=20),
            )
        )
    placements = exc.value.details["placements"]
    assert any("overlaps" in m for m in placements["a"])
    assert any("outside" in m for m in placements["c"])
    assert any("unknown building" in m for m in placements["d"])


def test_summarize_power_and_cost() -> None:
    # Smelter: 4 MW, cost {iron-rod:5, wire:8}. Two smelters at 100% clock.
    summary = summarize(
        _layout(
            Placement(id="a", building="smelter", x=0, y=0),
            Placement(id="b", building="smelter", x=10, y=0, clock=2.0),
        )
    )
    assert summary.machine_count == 2
    assert summary.machine_counts == {"smelter": 2}
    assert summary.build_cost == {"iron-rod": 10, "wire": 16}
    # clock 1.0 -> 4 MW; clock 2.0 -> 4 * 2^1.321928 ≈ 9.999 MW.
    assert summary.total_power_mw == pytest.approx(4 + 4 * 2**1.321928, rel=1e-4)


async def test_plan_crud_and_versioning(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/plans",
        json={
            "name": "Iron line",
            "layout": {
                "grid": {"width": 40, "length": 40, "cell_cm": 100},
                "placements": [{"id": "s1", "building": "smelter", "x": 0, "y": 0}],
            },
        },
    )
    assert created.status_code == 201
    plan = created.json()
    assert plan["version"] == 1
    assert plan["summary"]["machine_count"] == 1
    plan_id = plan["id"]

    # Update layout -> new version.
    updated = await client.put(
        f"/api/v1/plans/{plan_id}",
        json={
            "comment": "add second smelter",
            "layout": {
                "grid": {"width": 40, "length": 40, "cell_cm": 100},
                "placements": [
                    {"id": "s1", "building": "smelter", "x": 0, "y": 0},
                    {"id": "s2", "building": "smelter", "x": 10, "y": 0},
                ],
            },
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["summary"]["machine_count"] == 2

    versions = (await client.get(f"/api/v1/plans/{plan_id}/versions")).json()
    assert [v["version"] for v in versions] == [1, 2]

    # Revert to v1 -> creates v3 with one smelter again.
    reverted = await client.post(f"/api/v1/plans/{plan_id}/revert/1")
    assert reverted.status_code == 200
    assert reverted.json()["version"] == 3
    assert reverted.json()["summary"]["machine_count"] == 1

    listing = (await client.get("/api/v1/plans")).json()
    assert any(p["id"] == plan_id and p["version"] == 3 for p in listing)


async def test_plan_rejects_invalid_layout(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/plans",
        json={
            "name": "Bad",
            "layout": {
                "grid": {"width": 5, "length": 5, "cell_cm": 100},
                "placements": [{"id": "s1", "building": "manufacturer", "x": 0, "y": 0}],
            },
        },
    )
    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "validation_failed"
    assert "s1" in body["details"]["placements"]


async def test_plan_export_import_roundtrip(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/plans",
        json={
            "name": "Export me",
            "description": "roundtrip",
            "layout": {
                "grid": {"width": 40, "length": 40, "cell_cm": 100},
                "placements": [
                    {"id": "s1", "building": "constructor", "x": 5, "y": 5, "clock": 1.5}
                ],
            },
        },
    )
    plan_id = created.json()["id"]
    exported = (await client.get(f"/api/v1/plans/{plan_id}/export")).json()
    assert exported["name"] == "Export me"
    assert "id" not in exported

    imported = await client.post("/api/v1/plans/import", json=exported)
    assert imported.status_code == 201
    new_plan = imported.json()
    assert new_plan["id"] != plan_id
    assert new_plan["layout"]["placements"][0]["clock"] == 1.5


async def test_plan_404s(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/plans/999999")).status_code == 404
    assert (await client.post("/api/v1/plans/999999/revert/1")).status_code == 404
