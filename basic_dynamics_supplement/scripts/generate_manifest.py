                      
"""Build the isolated Stage-1 supplement design manifest.

The source rows are accepted Stage-1 no-enemy episodes, used only as
allow-listed map/anchor/loadout templates.  Every generated episode has a
new deterministic action schedule and remains training_admitted=false until
the supplement receives its own final audit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = Path(
    "./xonotic_workspace"
    "stage1_foundation_v5_formal_56x1_runtime_r5/input.jsonl"
)
ACCEPTED_MANIFEST = Path(
    "./rigen_data/manifests/"
    "stage1_foundation_v5_accepted_postfiltered_r1_20260730/"
    "accepted_filtered.jsonl"
)
BUILD = ROOT / "build/capture-ddb4838d778d-qc7e8310-aarch64"
PORTABLE_DATA_ROOT = Path("./rigen_data")
ROUTE_ACTION_ROOT = ROOT / "route_actions"
OUTPUT = ROOT / "manifests/design.jsonl"
AUDIT = ROOT / "manifests/DESIGN_AUDIT.json"

SOURCE_COMMIT = "ddb4838d778d7c3ceee245212a1c8e2bf0998bd0"
OFFLINE_DEMO_PATCH_SHA256 = (
    "be8a052d825cffa9b28ecd8ee384272bd16a8fbf3848cd45ba9a519f51194a3d"
)
QC_SOURCE_COMMIT = "7e8310b0d0c135774f5cfbdb08122eec1f12c99b"
QC_SHA256 = {
    "csprogs.dat": "bee1e4be8b41237266c50aad6f59a7a87687c809064a278dc8553f1d734f7498",
    "menu.dat": "f02ae3b5396aa8d5d8f36a43c11204d33ce92c35379e5ecd32590da6677529a4",
    "progs.dat": "37909a11c5bba198d6e76f669bb9d3dda21638d29a308e8063a834821b013600",
}
RUNTIME_LOCK = ROOT / "locks/capture-ddb4838d778d-qc7e8310-aarch64.sha256"
RUNTIME_LOCK_SHA256 = (
    "916ded53fd9a05d87072e06ca63a8ee6bbc539bb665fa5faeb1cdb20d7275a4c"
)
ACTION_PROGRAM = "stage1_supplement_v1"
WEAPONS = (
    "Blaster",
    "Crylink",
    "Devastator",
    "Electro",
    "Hagar",
    "MachineGun",
    "Mortar",
    "Shotgun",
    "Vortex",
)
IMPACT_MAPS = ("boil", "darkzone", "implosion", "xoylent")

TRAIN_COUNTS = {
    "idle_pure": 2500,
    "idle_then_action": 750,
    "action_then_idle": 375,
    "action_idle_action": 375,
    "wall_impact": 1152,
    "smooth_route": 2000,
}
HELDOUT_COUNTS = {
    "idle_pure": 136,
    "idle_then_action": 40,
    "action_then_idle": 20,
    "action_idle_action": 20,
    "wall_impact": 72,
    "smooth_route": 96,
}

DROP_TEMPLATE_FIELDS = {
    "assigned_shard",
    "candidate_ordinal",
    "candidate_wave",
    "certified_collision",
    "certified_realized_motion",
    "counterfactual_group_id",
    "data_spec_sha256",
    "fixed_variant_index",
    "frozen_actions_path",
    "frozen_actions_sha256",
    "path_prototype",
    "path_prototype_data_spec_sha256",
    "player_path_certificate",
    "player_path_generation",
    "player_path_runtime_compatibility",
    "review_action",
    "route_group_id",
    "route_plan",
    "route_request",
    "route_view_policy",
    "semantic_variant",
    "shard_count",
    "source_commit_required",
    "targeted_candidate",
}


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def group_id(row: dict[str, Any]) -> str:
    return str(
        row.get("source_prototype_id")
        or row.get("counterfactual_group_id")
        or row["episode_id"]
    )


def deterministic_order(
    rows: Iterable[dict[str, Any]], salt: str
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f"{salt}:{row['episode_id']}".encode()
        ).hexdigest(),
    )


def clean_template(
    template: dict[str, Any],
    *,
    episode_id: str,
    ordinal: int,
    role: str,
    split_role: str,
    supplement: dict[str, Any],
    expects_sound: bool,
    fire_required: bool,
) -> dict[str, Any]:
    scenario = copy.deepcopy(template)
    for key in DROP_TEMPLATE_FIELDS:
        scenario.pop(key, None)
    source_episode_id = str(template["episode_id"])
    source_group_id = group_id(template)
    template_jump = bool(
        (template.get("action_design") or {}).get("jump", False)
    )
    scenario.update(
        {
            "schema_version": "xonotic-v2-scenario-v1",
            "episode_id": episode_id,
            "seed": 281_000_000 + ordinal,
            "split": "foundation_no_enemy",
            "dataset_role": "foundation_no_enemy",
            "training_stage": "stage1",
            "training_admitted": False,
            "formal_collection_authorized": True,
            "formal_authorization_basis": (
                "stage1_supplement_v1_user_authorized_20260810"
            ),
            "source_commit_required": SOURCE_COMMIT,
            "qc_source_commit_required": QC_SOURCE_COMMIT,
            "runtime_lock_sha256": RUNTIME_LOCK_SHA256,
            "action_program": ACTION_PROGRAM,
            "acceptance_policy": "tiered_review_v1",
            "target_bin": "foundation_no_enemy",
            "intent_outcome": "none",
            "enemy": None,
            "enemy_present": False,
            "enemy_model": "",
            "enemy_skin": 0,
            "enemy_color": 0,
            "expects_sound": expects_sound,
            "acceptance": {
                "actual_outcome": None,
                "fire_required": fire_required,
                "reload_success": False,
            },
            "collision_design": None,
            "candidate_wave": "supplement_primary",
            "candidate_ordinal": ordinal,
            "primary_bucket": role,
            "category": role,
            "supplement_split": split_role,
            "supplement_source_episode_id": source_episode_id,
            "supplement_source_group_id": source_group_id,
            "supplement": {
                "schema_version": "xonotic-stage1-supplement-action-v1",
                **supplement,
            },
            "scheduler_targets": {
                "supplement_category": role,
                "supplement_split": split_role,
                "camera_max_frame_step_deg": 6.0,
            },
        }
    )
                                                                   
                                                          
    scenario["action_design"] = {
        "schema_version": "xonotic-stage1-supplement-action-design-v1",
        "model_action_schema_version": "ltx2-crossfps-xonotic-v1",
        "mode": role,
        "action_family": supplement.get("action_family", role),
        "weapon_action": (
            "environmental_primary" if fire_required else "none"
        ),
        "jump": bool(
            role == "smooth_route"
            and supplement.get("preserve_jump", False)
            and template_jump
        ),
        "weapon_select": False,
        "zoom": False,
    }
    return scenario


def materialize_route_actions(certificate: dict[str, Any]) -> tuple[str, str]:
    relative_source = Path(str(certificate["actions_path"]))
    if relative_source.is_absolute() or ".." in relative_source.parts:
        raise RuntimeError(f"unsafe route action path: {relative_source}")
    source = PORTABLE_DATA_ROOT / relative_source
    expected = str(certificate["actions_sha256"])
    if not source.is_file():
        raise RuntimeError(f"missing route action source: {source}")
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f"route action source hash mismatch: {source}")
    destination = ROUTE_ACTION_ROOT / f"{expected}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f"materialized route action hash mismatch: {destination}")
    return str(destination.relative_to(ROOT)), expected


def allocate_heldout_groups(
    eligible: list[dict[str, Any]],
    impact_rows: dict[tuple[str, str], list[dict[str, Any]]],
    route_rows: list[dict[str, Any]],
) -> tuple[set[str], dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    heldout_groups: set[str] = set()
    impact_selection: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for map_name in IMPACT_MAPS:
        by_group: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for weapon in WEAPONS:
            for row in impact_rows[map_name, weapon]:
                by_group[group_id(row)][weapon] = row
        complete_groups = sorted(
            (
                gid
                for gid, weapon_rows in by_group.items()
                if set(WEAPONS) <= set(weapon_rows)
            ),
            key=lambda gid: hashlib.sha256(
                f"heldout-impact-group-{map_name}-{gid}".encode()
            ).hexdigest(),
        )
        if len(complete_groups) < 2:
            raise RuntimeError(
                f"not enough complete heldout impact groups for {map_name}"
            )
        selected_map_groups = complete_groups[:2]
        heldout_groups.update(selected_map_groups)
        for weapon in WEAPONS:
            impact_selection[map_name, weapon] = [
                by_group[gid][weapon] for gid in selected_map_groups
            ]

    route_selection: list[dict[str, Any]] = []
    for row in deterministic_order(route_rows, "heldout-route"):
        gid = group_id(row)
        if gid in heldout_groups:
            continue
        route_selection.append(row)
        heldout_groups.add(gid)
        if len(route_selection) == HELDOUT_COUNTS["smooth_route"]:
            break
    if len(route_selection) != HELDOUT_COUNTS["smooth_route"]:
        raise RuntimeError("not enough heldout route groups")

    idle_needed = sum(
        HELDOUT_COUNTS[key]
        for key in (
            "idle_pure",
            "idle_then_action",
            "action_then_idle",
            "action_idle_action",
        )
    )
    idle_selection: list[dict[str, Any]] = []
    for row in deterministic_order(eligible, "heldout-idle"):
        gid = group_id(row)
        if gid in heldout_groups:
            continue
        idle_selection.append(row)
        heldout_groups.add(gid)
        if len(idle_selection) == idle_needed:
            break
    if len(idle_selection) != idle_needed:
        raise RuntimeError("not enough heldout idle groups")
    return heldout_groups, impact_selection, route_selection, idle_selection


def main() -> None:
    if (BUILD / "SOURCE_COMMIT").read_text().strip() != SOURCE_COMMIT:
        raise RuntimeError("isolated build source commit mismatch")
    if (BUILD / "QC_SOURCE_COMMIT").read_text().strip() != QC_SOURCE_COMMIT:
        raise RuntimeError("isolated build QC source commit mismatch")
    for name, expected in QC_SHA256.items():
        if hashlib.sha256((BUILD / "qc" / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"isolated build QC hash mismatch: {name}")
    if hashlib.sha256(RUNTIME_LOCK.read_bytes()).hexdigest() != RUNTIME_LOCK_SHA256:
        raise RuntimeError("isolated runtime lock hash mismatch")
    for line in RUNTIME_LOCK.read_text().splitlines():
        expected, relative = line.split(maxsplit=1)
        path = (ROOT / relative.strip()).resolve()
        if BUILD.resolve() not in path.parents:
            raise RuntimeError(f"runtime lock path outside build: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"runtime lock entry mismatch: {path}")
    source_rows = load_jsonl(SOURCE_MANIFEST)
    source_by_id = {row["episode_id"]: row for row in source_rows}
    accepted = load_jsonl(ACCEPTED_MANIFEST)

    eligible_records = [
        row
        for row in accepted
        if row.get("dataset_role") == "foundation_no_enemy"
        and row.get("post_collection_screening", {}).get("decision") == "keep"
        and float(
            row.get("actual", {})
            .get("motion", {})
            .get("yaw_max_frame_step_deg", 99)
        )
        <= 6.0
        and float(
            row.get("actual", {})
            .get("motion", {})
            .get("pitch_max_frame_step_deg", 99)
        )
        <= 6.0
        and row["episode_id"] in source_by_id
    ]
    eligible = [source_by_id[row["episode_id"]] for row in eligible_records]
    accepted_by_id = {row["episode_id"]: row for row in eligible_records}

    impact_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    route_rows: list[dict[str, Any]] = []
    for source in eligible:
        record = accepted_by_id[source["episode_id"]]
        if (
            record.get("primary_bucket") == "weapon_environment"
            and record.get("map") in IMPACT_MAPS
            and record.get("weapon") in WEAPONS
            and int(record.get("qa", {}).get("fire_count", 0)) > 0
        ):
            impact_rows[record["map"], record["weapon"]].append(source)
        if (
            record.get("primary_bucket") == "route_action"
            and int(record.get("qa", {}).get("fire_count", 0)) == 0
            and int(record.get("qa", {}).get("damage_count", 0)) == 0
            and (source.get("player_path_certificate") or {}).get("actions_path")
        ):
            route_rows.append(source)

    heldout_groups, heldout_impacts, heldout_routes, heldout_idle = (
        allocate_heldout_groups(eligible, impact_rows, route_rows)
    )
    train_eligible = [
        row for row in eligible if group_id(row) not in heldout_groups
    ]
    train_routes = [
        row for row in route_rows if group_id(row) not in heldout_groups
    ]

    rows: list[dict[str, Any]] = []
    ordinal = 0

    def add(
        template: dict[str, Any],
        *,
        role: str,
        split_role: str,
        supplement: dict[str, Any],
        expects_sound: bool,
        fire_required: bool,
    ) -> None:
        nonlocal ordinal
        ordinal += 1
        short_role = {
            "idle_pure": "idle",
            "idle_then_action": "i2a",
            "action_then_idle": "a2i",
            "action_idle_action": "aia",
            "wall_impact": "imp",
            "smooth_route": "rte",
        }[role]
        episode_id = f"s1sup_{split_role[:2]}_{short_role}_{ordinal:06d}"
        rows.append(
            clean_template(
                template,
                episode_id=episode_id,
                ordinal=ordinal,
                role=role,
                split_role=split_role,
                supplement=supplement,
                expects_sound=expects_sound,
                fire_required=fire_required,
            )
        )

    idle_roles = (
        "idle_pure",
        "idle_then_action",
        "action_then_idle",
        "action_idle_action",
    )
    train_idle_templates = deterministic_order(train_eligible, "train-idle")
    cursor = 0
    for role in idle_roles:
        for index in range(TRAIN_COUNTS[role]):
            template = train_idle_templates[cursor % len(train_idle_templates)]
            cursor += 1
            action_family = ("view", "move", "view_move")[index % 3]
            add(
                template,
                role=role,
                split_role="train",
                supplement={
                    "mode": role,
                    "action_family": action_family,
                    "variant": index,
                },
                expects_sound=False,
                fire_required=False,
            )

    heldout_cursor = 0
    for role in idle_roles:
        for index in range(HELDOUT_COUNTS[role]):
            template = heldout_idle[heldout_cursor]
            heldout_cursor += 1
            action_family = ("view", "move", "view_move")[index % 3]
            add(
                template,
                role=role,
                split_role="heldout",
                supplement={
                    "mode": role,
                    "action_family": action_family,
                    "variant": index + 100_000,
                },
                expects_sound=False,
                fire_required=False,
            )

    trajectory_names = (
        "horizontal",
        "vertical",
        "diagonal",
        "arc",
        "zigzag",
        "random_smooth",
    )
    for map_name in IMPACT_MAPS:
        for weapon in WEAPONS:
            train_templates = [
                row
                for row in deterministic_order(
                    impact_rows[map_name, weapon],
                    f"train-impact-{map_name}-{weapon}",
                )
                if group_id(row) not in heldout_groups
            ]
            if not train_templates:
                raise RuntimeError(f"no train impact templates {map_name}/{weapon}")
            for index in range(32):
                template = train_templates[index % min(8, len(train_templates))]
                add(
                    template,
                    role="wall_impact",
                    split_role="train",
                    supplement={
                        "mode": "wall_impact",
                        "scene_style": map_name,
                        "trajectory": trajectory_names[index % len(trajectory_names)],
                        "trajectory_variant": index,
                    },
                    expects_sound=True,
                    fire_required=True,
                )
            for index, template in enumerate(heldout_impacts[map_name, weapon]):
                add(
                    template,
                    role="wall_impact",
                    split_role="heldout",
                    supplement={
                        "mode": "wall_impact",
                        "scene_style": map_name,
                        "trajectory": trajectory_names[(index + 4) % len(trajectory_names)],
                        "trajectory_variant": index + 100_000,
                    },
                    expects_sound=True,
                    fire_required=True,
                )

    train_routes_ordered = deterministic_order(train_routes, "train-route")
    for split_role, count, templates, offset in (
        ("train", TRAIN_COUNTS["smooth_route"], train_routes_ordered, 0),
        ("heldout", HELDOUT_COUNTS["smooth_route"], heldout_routes, 100_000),
    ):
        if len(templates) < count:
            raise RuntimeError(f"not enough {split_role} route templates")
        for index, template in enumerate(templates[:count]):
            certificate = template["player_path_certificate"]
            base_actions_path, base_actions_sha256 = materialize_route_actions(
                certificate
            )
            add(
                template,
                role="smooth_route",
                split_role=split_role,
                supplement={
                    "mode": "smooth_route",
                    "base_actions_path": base_actions_path,
                    "base_actions_sha256": base_actions_sha256,
                    "overlay": ("sweep", "scan", "vertical", "figure8")[index % 4],
                    "overlay_variant": index + offset,
                    "view_scale": (0.72, 0.78, 0.84, 0.90)[index % 4],
                    "preserve_jump": index % 5 == 0,
                },
                expects_sound=False,
                fire_required=False,
            )

    expected_total = sum(TRAIN_COUNTS.values()) + sum(HELDOUT_COUNTS.values())
    if len(rows) != expected_total or ordinal != expected_total:
        raise AssertionError((len(rows), ordinal, expected_total))
    observed = Counter((row["supplement_split"], row["primary_bucket"]) for row in rows)
    for role, count in TRAIN_COUNTS.items():
        if observed["train", role] != count:
            raise AssertionError(("train", role, observed["train", role], count))
    for role, count in HELDOUT_COUNTS.items():
        if observed["heldout", role] != count:
            raise AssertionError(("heldout", role, observed["heldout", role], count))

    train_groups = {
        row["supplement_source_group_id"]
        for row in rows
        if row["supplement_split"] == "train"
    }
    test_groups = {
        row["supplement_source_group_id"]
        for row in rows
        if row["supplement_split"] == "heldout"
    }
    overlap = train_groups & test_groups
    if overlap:
        raise AssertionError(f"train/heldout source-group overlap: {sorted(overlap)[:10]}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical(row) + "\n" for row in rows)
    OUTPUT.write_text(payload, encoding="utf-8")
    manifest_sha256 = hashlib.sha256(payload.encode()).hexdigest()
    impact_counts = Counter(
        (
            row["supplement_split"],
            row["map"],
            row["weapon"],
        )
        for row in rows
        if row["primary_bucket"] == "wall_impact"
    )
    audit = {
        "schema_version": "xonotic-stage1-supplement-design-audit-v1",
        "manifest": str(OUTPUT),
        "manifest_sha256": manifest_sha256,
        "source_manifest": str(SOURCE_MANIFEST),
        "source_manifest_sha256": hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest(),
        "accepted_template_manifest": str(ACCEPTED_MANIFEST),
        "accepted_template_manifest_sha256": hashlib.sha256(ACCEPTED_MANIFEST.read_bytes()).hexdigest(),
        "runtime_source_commit": SOURCE_COMMIT,
        "offline_demo_fixedstep_patch_sha256": OFFLINE_DEMO_PATCH_SHA256,
        "qc_source_commit": QC_SOURCE_COMMIT,
        "qc_sha256": QC_SHA256,
        "runtime_lock": str(RUNTIME_LOCK),
        "runtime_lock_sha256": RUNTIME_LOCK_SHA256,
        "rows": len(rows),
        "video_seconds_per_episode": 5,
        "video_hours": len(rows) * 5 / 3600,
        "counts": {
            split: {
                role: observed[split, role]
                for role in TRAIN_COUNTS
            }
            for split in ("train", "heldout")
        },
        "impact_cell_counts": {
            f"{split}/{map_name}/{weapon}": count
            for (split, map_name, weapon), count in sorted(impact_counts.items())
        },
        "impact_maps": list(IMPACT_MAPS),
        "weapons": list(WEAPONS),
        "train_source_groups": len(train_groups),
        "heldout_source_groups": len(test_groups),
        "train_heldout_source_group_overlap": 0,
        "training_admitted": False,
        "existing_stage1_stage2_mutated": False,
    }
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
