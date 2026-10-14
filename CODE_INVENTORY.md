# RIGen dataset construction code inventory

This inventory describes the minimal construction release for the four RIGen Xonotic dataset routes.

- `common_capture/`: shared capture runtime, patches, source snapshots, build helpers, and upstream licenses.
- `basic_dynamics_supplement/`: Basic Dynamics Stage-1 supplement and release finalization.
- `interaction_short/`: short Interaction capture, validation, and postprocessing.
- `interaction_long/`: Interaction-Long capture and release tooling.
- `arena/`: Arena duel capture, rollout, prompt, and release tooling.
- `requirements-reproduction.txt`: unpinned non-GPU Python dependencies for route utilities.

The route directories include the modified Xonotic and QuakeC source snapshots required by the capture logic. Captured media, raw demos, logs, checkpoints, production outputs, and private machine state are excluded.
