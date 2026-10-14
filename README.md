# RIGen Xonotic data-generation code

RIGen is a reusable data-generation toolkit for interactive game-world research. This repository provides the capture runtime, Xonotic and QuakeC modifications, route templates, scenario and manifest builders, telemetry processing, validation, and release assembly code.

The four routes used in the paper are included as working examples:

- **Basic Dynamics**: player-controlled local dynamics and state/action telemetry.
- **Interaction short**: short opponent-motion interaction blocks with outcomes and visibility labels.
- **Interaction-Long**: longer multi-block interaction trajectories.
- **Arena**: duel trajectories with combat, visibility, prompt, and rollout processing.

The main purpose of this repository is reuse. You can use the shared capture and manifest layers to define new maps, weapons, appearance combinations, movement policies, action contracts, opponent behaviors, camera conditions, event labels, and dataset splits. The paper routes are reference implementations, not the only supported dataset designs.

## What this repository produces

A normal run has this flow:

```text
scenario and action specification
        -> route manifest builder
        -> Xonotic and QuakeC runtime
        -> captured episode telemetry and audiovisual files
        -> episode validator and QA filters
        -> training and evaluation manifests
        -> release package
```

The code can produce both the local route manifests that drive capture and the final JSONL manifests that index accepted episodes. The captured media and generated manifests belong in a data/output workspace, not in the code repository.

## Repository map

```text
common_capture/
  shared capture runtime, patches, source snapshots, build helpers, validators
basic_dynamics_supplement/
  Basic Dynamics supplement and release assembly
interaction_short/
  short-interaction route templates, scenario builders, runners, validators
interaction_long/
  long-interaction route templates, lifecycle and manifest tools
arena/
  Arena QuakeC source, rollout, visibility, prompt and release tools
requirements.txt
  base Python packages used by route utilities
release_manifest.json
  inventory of this code release
LICENSE.md and NOTICE
  component licensing and upstream attribution
```

## Install

This is a script-and-source repository, not an installable Python package. There is no `pip install .` step.

The supported baseline is Linux with Python 3, Bash, Git, FFmpeg, SDL2, OpenGL/EGL, and a compatible GPU runtime. On Ubuntu or Debian, install the system tools used by the included fetch and build scripts:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config git curl unzip zip ffmpeg jq rsync python3 python3-venv python3-pip libsdl2-2.0-0 libsdl2-dev libegl-dev libgl-dev libgles-dev libglvnd-core-dev libglvnd-dev libglx-dev libopengl-dev mesa-utils-bin
```

Create the base Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Some route utilities use PyTorch or other GPU-specific libraries. Install a PyTorch build that matches the machine's CUDA, ROCm, or CPU runtime separately. `requirements.txt` deliberately does not choose a GPU build for the user.

Set a local workspace. These variables are the public interface used by the route scripts:

```bash
export RIGEN_CODE_ROOT="$PWD"
export RIGEN_DATA_ROOT="$PWD/rigen_data"
export RIGEN_OUTPUT_ROOT="$PWD/rigen_outputs"
export XONOTIC_SOURCE_ROOT="$PWD/xonotic_workspace"
export XONOTIC_CAPTURE_ROOT="$XONOTIC_SOURCE_ROOT"
```

Fetch and verify the official Xonotic 0.8.6 archives, extract the game assets, prepare the local graphics sysroot, and build the baseline runtime:

```bash
bash common_capture/scripts/fetch_official_086.sh
bash common_capture/scripts/extract_official_086.sh
bash common_capture/scripts/prepare_local_sysroot.sh
bash common_capture/scripts/build_release_arm64.sh
```

The ARM64 build scripts are reference commands. On x86_64, use the corresponding x86 build helpers and install the local SDL/OpenGL development packages. The scripts record downloaded-archive checksums under the local workspace so that an environment can be rebuilt without relying on a hidden machine path.

## Reusing the code for a new dataset

Start with the route whose timing and observation contract is closest to the dataset you want to build. Keep a new route in its own directory or branch so that its schema and acceptance rules remain explicit.

### 1. Define the data contract

Write down the episode duration, simulation tick rate, output frame rate, action channels, camera controls, state fields, event vocabulary, visibility policy, acceptance rules, and train/validation/test split. Use the existing route configs and manifest schemas as templates. Give the new route a new schema or release identifier instead of silently changing an existing one.

### 2. Build the scenario and action manifests

Scenario builders turn local tables and policy parameters into capture-ready JSONL manifests. Inspect the available arguments before running one:

```bash
python common_capture/scripts/prepare_stage1_v5_manifests.py --help
python interaction_short/production_scripts/prepare_stage2_short_42k_v15_random_fire_manifest.py --help
python interaction_long/pilot_scripts/long60_production_ref42_v8_collision_camera.py --help
python arena/scripts/build_authoritative_actions.py --help
```

For a new dataset, copy the nearest builder, change its route identifier and output root, and preserve the original source tables. A builder should write a new manifest directory and an audit file; it should not overwrite an input manifest.

### 3. Add or change game behavior

Shared capture hooks and telemetry are under `common_capture`. Route-specific behavior belongs in the route's source, patch, or configuration directory. Arena behavior is implemented in `arena/source/qcsrc` and built with the Arena scripts. Use the patch files when you need to port a change to a clean Xonotic source tree; use the included source snapshot when you need the exact reference implementation.

### 4. Run capture workers

The generic capture and shard runners are under `common_capture/scripts`. Route-specific runners are under `interaction_short/production_scripts`, `interaction_long/pilot_scripts`, and `arena/production_scripts`.

Inspect a runner before launching a large job:

```bash
python common_capture/scripts/run_capture_manifest_shard.py --help
bash common_capture/scripts/run_stage1_56x1_worker.sh --help
python interaction_short/production_scripts/run_stage2_short_42k_activeonly_v15_multigpu.py --help
python interaction_long/pilot_scripts/long60_production_ref42_v8_collision_camera.py --help
bash arena/scripts/process_recorded_episode.sh --help
```

Provide a local manifest root, a local output root, the Xonotic source/build root, and a machine-specific worker configuration. A worker writes episode media and authoritative telemetry to the output workspace. It does not write back into the source tree.

### 5. Validate and assemble a release

Use the route validators before accepting an episode. Then generate the final manifest and provenance maps:

```bash
python basic_dynamics_supplement/scripts/finalize_training_release.py --help
python basic_dynamics_supplement/scripts/generate_manifest.py --help
python common_capture/scripts/finalize_provenance.py --help
python arena/scripts/build_duel_v11_data_review.py --help
```

Keep the accepted episode records, source hashes, action schema, QA reports, and generated manifest together. This is what makes a new dataset version independently inspectable and reproducible.

## Reproducing the four paper routes

The following entrypoints reproduce the paper route logic after the external runtime, assets, and local inputs have been installed:

| Route | Prepare | Capture or production | Finalize |
|---|---|---|---|
| Basic Dynamics | `common_capture/scripts/prepare_stage1_v5_manifests.py` | `common_capture/scripts/run_stage1_56x1_worker.sh` | `basic_dynamics_supplement/scripts/finalize_training_release.py`, `generate_manifest.py` |
| Interaction short | `interaction_short/production_scripts/prepare_stage2_short_42k_v15_random_fire_manifest.py` | `interaction_short/production_scripts/` | matching `run_stage2_*`, `finalize_*`, and manifest tools |
| Interaction-Long | `interaction_long/pilot_scripts/long60_production_ref42_v8_collision_camera.py` | `interaction_long/scripts/` and `pilot_scripts/` | long-route release and merge tools |
| Arena | Arena action and rollout builders under `arena/scripts/` | `arena/production_scripts/` | Arena action, visibility, prompt, and review builders |

The exact paper release also depends on the paper's frozen route configuration and accepted-input snapshot. The code release supplies the construction logic; it does not include the captured media or private production state.

## What belongs in a data release instead of this code repository

Do not commit generated or machine-specific material to the code repository:

- captured video, audio, frame tables, raw demos, and episode directories;
- generated scenario, action, QA, provenance, or training manifests for a particular run;
- build directories, compiled binaries, QuakeC outputs, local sysroots, downloaded archives, and package caches;
- logs, profiler output, temporary files, checkpoints, virtual environments, and scheduler job output;
- private hostnames, account names, mount paths, credentials, tokens, or machine-specific configuration;
- large experiment results or a dataset release assembled from accepted episodes.

Commit reusable source, route templates, schema definitions, small public examples, and changes needed to regenerate those outputs. Publish a generated dataset and its manifests as a separate data release, with the code commit and route version recorded in its provenance.

## Quick sanity check

From the repository root, these commands check the source tree without starting a capture:

```bash
python -m compileall common_capture basic_dynamics_supplement interaction_short interaction_long arena
python - <<'PY'
import json
from pathlib import Path
json.load(Path("release_manifest.json").open())
print("release manifest is valid")
PY
```

A full capture still requires the external Xonotic assets, local scenario inputs, a compatible renderer, and the machine's GPU runtime.

## Licensing

This is a component-licensed code release. RIGen-authored orchestration code, configuration templates, patches, and documentation are released under the terms in `LICENSE.md`. Modified Xonotic, DarkPlaces, and gmqcc material remains under its applicable upstream GPL or project terms. Preserve `NOTICE` and the upstream license texts under `common_capture/licenses/` when redistributing.
