# RIGen Xonotic dataset construction code

This repository contains the reproducible construction code for the four RIGen Xonotic dataset components:

- Basic Dynamics
- Interaction short
- Interaction-Long
- Arena

It contains route scripts, configuration templates, capture patches, modified Xonotic and QuakeC source snapshots, validation tools, and upstream notices. It does not contain captured media, episode outputs, raw demos, logs, checkpoints, private cluster state, or development archives.

## Repository layout

```text
common_capture/              shared capture runtime, patches, source, and licenses
basic_dynamics_supplement/   Basic Dynamics supplement and release finalization
interaction_short/           short interaction capture, validation, and manifests
interaction_long/            long interaction capture and release tooling
arena/                       Arena QuakeC source and rollout/release tooling
CODE_INVENTORY.md            release inventory
release_manifest.json        file inventory with byte sizes
requirements-reproduction.txt Python packages used by route utilities
LICENSE.md                   component licensing and upstream terms
NOTICE                       attribution and provenance notice
```

## Requirements

The original collection used Linux, Python 3, Bash, FFmpeg, SDL/OpenGL, the official Xonotic 0.8.6 source and assets, and multi-GPU workers. The release does not bundle a Python environment, GPU driver, container image, or external Xonotic download.

Install the required tools on the target machine and provide local paths through the environment variables below. The defaults are relative to the repository and contain no machine-specific paths.

```bash
export RIGEN_CODE_ROOT="$PWD"
export RIGEN_DATA_ROOT="$PWD/rigen_data"
export RIGEN_OUTPUT_ROOT="$PWD/rigen_outputs"
export XONOTIC_SOURCE_ROOT="$PWD/xonotic_workspace"
```

Set additional route-specific variables when a script documents them. The route preparers in this repository generate the local scenario and training manifests; users do not need to hand-write those manifests. Keep generated manifests and media under `RIGEN_DATA_ROOT` and `RIGEN_OUTPUT_ROOT`; do not commit them to this repository.

## Install and initialize

On Ubuntu or Debian, install the system tools used by the fetch, extraction, build, and validation scripts:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config git curl unzip zip ffmpeg jq rsync python3 python3-venv python3-pip libsdl2-2.0-0 libsdl2-dev libegl-dev libgl-dev libgles-dev libglvnd-core-dev libglvnd-dev libglx-dev libopengl-dev mesa-utils-bin
```

Create an isolated Python environment and install the non-GPU Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-reproduction.txt
```

Install a matching PyTorch build separately when a route uses Torch or a GPU worker. The correct command depends on the local CUDA, ROCm, or CPU runtime. The repository does not pin or redistribute GPU drivers.

Fetch and verify the official Xonotic 0.8.6 archives, extract the assets, prepare the local SDL/OpenGL sysroot, and build the baseline runtime:

```bash
export XONOTIC_CAPTURE_ROOT="$XONOTIC_SOURCE_ROOT"
bash common_capture/scripts/fetch_official_086.sh
bash common_capture/scripts/extract_official_086.sh
bash common_capture/scripts/prepare_local_sysroot.sh
bash common_capture/scripts/build_release_arm64.sh
```

`prepare_local_sysroot.sh` and `build_release_arm64.sh` target native ARM64. On x86_64, use the corresponding x86 build scripts under `common_capture/scripts` and provide the locally installed SDL/OpenGL development packages. Every fetch and extraction step writes checksums under the local `locks/` directory.

## Manifest generation

The repository includes the code that creates the local input and training manifests used by the capture routes. Start each entrypoint with `--help` to inspect its local source and output arguments before running it:

```bash
python common_capture/scripts/prepare_stage1_v5_manifests.py --help
python basic_dynamics_supplement/scripts/generate_manifest.py --help
python interaction_short/production_scripts/prepare_stage2_short_42k_v15_random_fire_manifest.py --help
python interaction_long/pilot_scripts/long60_production_ref42_v8_collision_camera.py --help
python arena/scripts/build_authoritative_actions.py --help
python arena/scripts/build_duel_v11_data_review.py --help
```

The manifest builders read local scenario tables, action schedules, source telemetry, and accepted capture records. They write JSONL manifests and audit metadata under the configured data or output root. The final data release is assembled from those generated manifests; no private prebuilt manifest is required by the code release.

## Reproduction routes

### Basic Dynamics

1. Prepare the Stage-1 route manifest with `common_capture/scripts/prepare_stage1_v5_manifests.py`.
2. Build the capture runtime with `common_capture/scripts/build_capture_arm64.sh` or the equivalent local build script.
3. Run the worker from `common_capture/scripts/run_stage1_56x1_worker.sh` with local manifest and output variables.
4. Apply the supplement and release checks in `basic_dynamics_supplement/scripts/finalize_training_release.py` and `generate_manifest.py`.

### Interaction short

1. Prepare the route with the `interaction_short/production_scripts/prepare_stage2_short_42k_v15_random_fire_manifest.py` entrypoint.
2. Run the selected launcher under `interaction_short/production_scripts` with a machine-specific worker configuration.
3. Validate and assemble the release with the matching `run_stage2_*`, `finalize_*`, and manifest scripts.

### Interaction-Long

1. Prepare the lifecycle route with `interaction_long/pilot_scripts/long60_production_ref42_v8_collision_camera.py`.
2. Run the approved long-sequence production entrypoint under `interaction_long/scripts` and `interaction_long/pilot_scripts`.
3. Build and validate the frozen train, validation, and test manifests with the long-route release scripts.

### Arena

1. Build the Arena QuakeC source under `arena/source/qcsrc` with the local Xonotic toolchain.
2. Prepare and run the rollout using `arena/scripts` and `arena/production_scripts`.
3. Assemble action, visibility, prompt, and reference manifests from the Arena release scripts.

Each route requires local manifests, Xonotic assets, an output directory, and a machine-specific worker configuration. The code supplies the route logic; it does not redistribute the large captured dataset.

## Path and privacy policy

All checked-in defaults use repository-relative paths or environment variables. Generated outputs should remain outside the source tree or under ignored paths. No server hostname, account name, cluster mount, private email, or machine-specific absolute path is part of this release.

## Validation before publishing

Run these checks from the repository root:

```bash
python -m compileall common_capture basic_dynamics_supplement interaction_short interaction_long arena
python - <<'PY'
import json
from pathlib import Path
p = Path('release_manifest.json')
json.load(p.open())
print('release manifest is valid')
PY
```

The capture scripts require the external runtime and assets, so a full render cannot be reproduced without those dependencies. The validation commands only check local source syntax and the release inventory.

## Licensing

This is a component-licensed code release. RIGen-authored orchestration code, configuration templates, patches, and documentation are released under the terms stated in `LICENSE.md`. Modified Xonotic, DarkPlaces, and gmqcc material remains under its applicable upstream GPL or project terms. Preserve the notices in `NOTICE` and `common_capture/licenses/` when redistributing.

## Provenance

`ORIGINAL_BACKUP_SHA256` records the checksum of the separate original code archive. The original archive contains development documentation and is not part of this minimal GitHub release.
