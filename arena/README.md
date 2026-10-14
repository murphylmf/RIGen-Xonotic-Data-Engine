# Xonotic duel-v11 Stage-2-aligned rollout lane

This is an isolated successor to `xonotic_capture_CCI_duel_v10_actions`.
It does not write into Stage-1, Stage-2, or duel-v10 outputs.

The lane records 60-second bot-vs-bot demos with authoritative 64 Hz actions,
renders a clean crosshair-only observation, replays final-camera visibility,
and emits both a 60-second 20 fps rollout and non-overlapping 4-second / 81-frame
training clips. Prompts use 5 x 0.8 second blocks. A block that is wholly
off-screen contains only: `The opponent is outside the player's view during
this block.`

The capture contract also fixes both bots to the official Seraphina model and
Machine Gun, removes pickups and all HUD except the crosshair, caps locomotion,
smooths the final recorded camera, suppresses attacks without mutual line of
sight, and admits respawns only when the opponent is not visibly present.

Process one admitted 60-second recording end to end with:

```bash
bash scripts/process_recorded_episode.sh DEMO_RUN_ID RENDER_RUN_ID
```

The currently validated four-rollout pilot is under
`outputs/batches/duel_v11_s2prompt_batch01_v4`. Its `TRAINING_READY.json`
requires both the static prompt/media gates and stratified reads through the
canonical AR and bidirectional training loader.

Run a conservative, sequential single-GPU ETA measurement only on an otherwise
idle GPU with:

```bash
bash scripts/benchmark_single_gpu.sh BENCHMARK_ID
```

The benchmark records a fresh rollout and includes rendering, both visibility
replays, prompt construction, and both 60-second and 4-second packaging. It
refuses to start if another GPU compute process is present.

For the production-like topology inherited from duel-v8, benchmark concurrent
60-second lanes with:

```bash
bash scripts/benchmark_concurrency.sh 8 BENCHMARK_ID
```

This keeps every lane's demo, render, visibility, release, temporary userdir,
and log separate. It reports the measured record-batch capacity, complete
post-processing capacity, and conservative end-to-end rate; cross-batch stage
overlap remains explicitly labeled as a projection until separately measured.
