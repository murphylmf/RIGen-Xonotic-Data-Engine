# Duel-v11 2-node x 4-GPU production

This lane creates eight independent global-rank outputs. Each DLC Worker Pod
owns four GPUs; each GPU is bound by UUID to one rank, with its own CPU set,
scratch tree, output tree, progress file, accepted shards, and rank-local AR and
bidirectional manifests. No process writes a global merged manifest.

Prepare a job file without submitting it:

```bash
cd ./xonotic_workspace
bash production_scripts/prepare_dlc_2x4_job.sh \
  TARGET_VIDEO_HOURS RUN_ID DLC_JOB_NAME
```

The preparation script writes an API-shaped JSON audit spec and prints the
exact flag-based `dlc submit pytorchjob` command, but never executes it. Do not
pass the audit JSON back through `dlc -f`: this DLC CLI version expects a
different job-file schema. The prepared topology is two Worker Pods, 4 GPUs
and 120 CPUs per Pod, eight global ranks total, with two concurrent episode
lanes per GPU by default. This keeps the CPU-bound recorder at roughly 15 CPU
cores per lane; the development-machine 8-lane benchmark consumed the full
120-core host and must not be multiplied by four GPU ranks inside one Pod.

On successful completion, every rank writes `RANK_COMPLETE.json` and then its
supervisor remains in an infinite heartbeat loop. The DLC job therefore stays
Running and retains all eight allocated GPUs until it is manually stopped.
Preflight failures and exhausted production retries also keep the Pod alive so
the allocation and logs are not lost silently.

Rank outputs are under:

```text
outputs/production_2x4/RUN_ID/ranks/rank_000/
...
outputs/production_2x4/RUN_ID/ranks/rank_007/
```

The development-machine reducer must only be run after all eight
`RANK_COMPLETE.json` files exist. Global merge is intentionally not performed
inside the DLC job.
