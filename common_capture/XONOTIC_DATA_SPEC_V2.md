# Xonotic 0.8.6 World-Model Data Specification v2.0

Status: canonical collection specification for the post-Pilot coverage work  
Updated UTC: 2026-07-27  
Official release: `xonotic-v0.8.6` only  
Current execution boundary: the bounded preflight, 24-episode
`v2_coverage_pilot`, and 24-episode `v2_motion_distance_pilot` are complete
and frozen. A separate bounded `v2_stage1_production_preflight` may validate
the reviewable production control flow; do not start either formal training
collection.

This document supersedes the old 15,804-episode production quota. The completed
100-episode legacy Pilot remains an immutable pipeline-validation artifact with
`split=pilot`; it is not eligible for Stage 1 or Stage 2 training.

## 1. Dataset and training hierarchy

The two datasets are collected, versioned, split, trained, and evaluated
separately.

| Training stage | Dataset role | First-release target | Video duration |
|---|---|---:|---:|
| Stage 1 | `foundation_no_enemy` | 45,000 | 62.50 h |
| Stage 1 | `foundation_enemy_distractor` | 15,000 | 20.83 h |
| Stage 2 | `causal_interaction` | 40,000 | 55.56 h |
| Total | three independent manifests | 100,000 | 138.89 h |

The 60k/40k values are collection budgets, not a joint training-mixture ratio.
Stage 2 begins from a Stage 1 checkpoint. Any Stage 1 replay during Stage 2 is a
training ablation that references the original Stage 1 IDs; it must not copy,
relabel, or merge the collection manifests.

Scaling gates:

- Stage 1: train/evaluate at 30k and 60k accepted episodes.
- Stage 2: train/evaluate at 20k and 40k accepted episodes.
- Expansion beyond these targets requires an observed scaling benefit.

## 2. Immutable per-episode media and simulation contract

- Authoritative simulation runs on a dedicated server at exactly 64 Hz.
- The client executes 64 hidden warm-up ticks and emits exactly 320 output
  ticks/frames.
- Output duration is exactly 5 seconds at 1280 x 720 and CFR 64 FPS.
- Camera projection is a fixed rectilinear `fov 90` in Xonotic's 4:3-base
  convention. At 1280 x 720 this must produce `frustum_x=1.333333333` and
  `frustum_y=0.750000000`, approximately 106.26 degrees horizontal by 73.74
  degrees vertical. Velocity zoom, spawn zoom, and action-triggered zoom are
  disabled. Every output frame must retain these intrinsics.
- Audio is engine-mixed 48 kHz signed 16-bit stereo with exactly 240,000
  samples/channel and 750 samples per video frame.
- Final media is MKV containing H.264 High, CRF 16, `yuv420p`, CFR 64, GOP 64,
  and FLAC audio.
- Encoding is CPU `libx264`; NVENC is forbidden.
- Keep only the first-person weapon model and crosshair. Disable damage text,
  hit indication, health, armor, ammo, score, timer, kill feed, chat, names,
  prompts, and all other HUD elements.
- Preserve and explicitly pin the official first-person weapon bob, follow,
  and lean behavior. Camera roll remains disabled. These weapon-model dynamics
  are not camera-intrinsic changes.
- Keep interaction SFX: movement, jump, landing, weapon primary/secondary
  action, confirmed reload for every reloadable core weapon, projectile,
  impact, explosion, hit, hurt, death, enemy movement, jump pad, and
  teleporter.
- Disable music, announcer, voice, chat, menu sounds, and unrelated global
  notifications.
- `SDL_AUDIODRIVER=dummy` is allowed while the sound engine remains active.
  `-nosound`, silent replacement, desktop recording, llvmpipe, and software
  rendering are forbidden.
- Controls are engine `usercmd` and yaw/pitch deltas, not raw keyboard,
  mouse, or HID.
- The collection keeps two action namespaces. `actions.parquet` is the
  complete 384-tick requested/sent/applied engine audit. A separate
  `model_actions.parquet` contains exactly one normalized action row for each
  of the 320 rendered frames and is the only default model-action input.
- `model_actions.parquet` follows the LTX-2 CrossFPS input contract. Continuous
  channels are ordered `[j_left.x, j_left.y, j_right.x, j_right.y]`, each in
  `[-1, 1]`. Physical-stick signs are used: left `+x` moves right, left `+y`
  moves backward, right `+x` turns right, and right `+y` looks down.
- The locked Xonotic decode is `forward=-400*j_left.y`,
  `strafe=400*j_left.x`, `yaw_delta=-12*j_right.x` degrees/tick, and
  `pitch_delta=12*j_right.y` degrees/tick. These are global schema constants;
  per-episode normalization, data-dependent gains, silent clipping, and
  fallback sign changes are forbidden.
- The eight model button slots are the LTX-2 canonical order
  `[A,B,X,Y,LB,RB,LT,RT]`. Xonotic binds `A=jump`, `X=reload`,
  `LT=secondary fire`, and `RT=primary fire`; the other four slots remain
  zero in v2. Every button value is exactly 0 or 1. Stage 1 retains the `LT`
  channel for LTX-2 schema compatibility but fixes it to zero; secondary-fire
  mechanics are deferred to a separately reviewed Stage 2 interaction set.
  Weapon selection and zoom remain released.
- Aiming means yaw/pitch control and target tracking. Xonotic 0.8.6 exposes a
  general FOV zoom action, and Vortex maps its default secondary input to that
  zoom, but it has no conventional weapon-model aim-down-sights transition.
  Zoom is excluded from v2 collection because every output frame must retain
  the locked FOV90 intrinsics; the zoom input remains released.
- Canonical engine state, render/camera state, final applied action, and
  collection-side privileged policy state must remain separate.

## 3. Official content policy

Only assets already present in the pinned official Xonotic 0.8.6 release may be
used. Automatic map download, community maps, `dlcache`, user-fork assets, and
unlocked packages are forbidden.

### 3.1 Maps

The official map archive contains 30 BSP files. `_hudsetup` is excluded, leaving
29 potential gameplay maps.

- 17 maps with ordinary DM spawns are first-line candidates.
- `implosion` is a DM-capable special case that requires waypoint placement.
- 11 CTF/race/assault/nexball or other mode maps require mode-specific
  preflight and HUD/audio suppression.

Stage 1 targets every map that passes live map, position, route, render, audio,
and determinism gates. Stage 2 targets every map that additionally passes
enemy-placement, line-of-sight, distance, and event-chain gates. A map may be
Stage-1-only; failed maps must be reported, not forced into the dataset.

### 3.2 Core weapons

The v2 core contains the nine non-hidden official `WEP_FLAG_NORMAL` weapons:

1. Blaster
2. Shotgun
3. MachineGun
4. Mortar
5. Electro
6. Crylink
7. Vortex
8. Hagar
9. Devastator

Hidden, super, mutator-only, and special-purpose weapons are excluded from the
v2 core. They require a separately versioned auxiliary dataset.

All nine core weapons may be held and fired through primary fire in Stage 1.
Weapon selection is not a v2 learning objective: each episode starts with its
declared weapon already active. Stage 1 does not schedule secondary fire
because the shared input mixes melee, burst, bounce, combo setup, pull,
charge/zoom, and remote detonation semantics. Stage 2 is also primary-only:
secondary fire, weapon selection, zoom/ADS, and reload remain zero. Stage 2
still requires weapon-specific hitscan/projectile, multi-projectile, bounce,
direct, splash, and pellet QA before a primary-fire sample is accepted.

Blaster has no ammo resource and is not reloadable. The other eight core
weapons use the official `WEP_FLAG_RELOADABLE` and generic reload
implementation. The stock Xonotic balance enables a clip only for MachineGun;
the locked v2 capture balance enables the same built-in reload path for
Shotgun, Mortar, Electro, Crylink, Vortex, Hagar, and Devastator as well.
Successful-reload examples are distributed approximately uniformly over these
eight reloadable weapons. Acceptance requires the declared weapon's
single linked `reload_start -> reload_complete` chain, exact weapon and actor,
exact locked two-second duration, clip increase to the declared capacity, and
reserve decrease. Interrupted, no-op, wrong-weapon, or post-death reloads are
rejected and replenished; they are never relabeled as successful reloads.

The locked clip capacities are:

| Reloadable weapon | Clip capacity | Reload time |
|---|---:|---:|
| Shotgun | 8 | 2 s |
| MachineGun | 60 | 2 s |
| Mortar | 16 | 2 s |
| Electro | 24 | 2 s |
| Crylink | 18 | 2 s |
| Vortex | 24 | 2 s |
| Hagar | 12 | 2 s |
| Devastator | 16 | 2 s |

### 3.3 Core enemy appearances

The v2 core contains the seven non-hidden standard official player models:

1. Erebus (`erebus`)
2. Gak Masked (`gakmasked`)
3. Ignis (`ignis`)
4. Nyx (`nyx`)
5. Pyria (`pyria`)
6. Seraphina (`seraphina`)
7. Umbra (`umbra`)

Each uses official skin indices 0 and 1, producing 14 core
`model x skin` appearances. Hidden IQM variants, Overkill DPM models, and other
special appearances are excluded.

Player color is a controlled secondary variable, not a full Cartesian
expansion. The first expansion preflight holds it to a small locked palette and
checks rendered identity. Model, skin, and color must be logged and allowlisted.

The first v2 release remains single-enemy so every causal chain has unambiguous
target identity. Multi-enemy scenes require a later spec version.

## 4. Stage 1: foundation dynamics

### 4.1 Learning objective

Stage 1 teaches:

- idle, forward, backward, left/right strafe;
- yaw and pitch with multiple amplitudes, signs, and temporal profiles;
- jump, airborne motion, landing, and vertical transitions;
- press/hold/release button edges;
- atomic, pairwise, and three-way action combinations;
- large linear, angular, and optical motion stability;
- held-weapon appearance without weapon/action confounding;
- primary action into the environment, projectile flight, world impact, and
  successful reload for every reloadable core weapon;
- ordinary routes, junctions, jump pads, teleporters, falls, collisions, and
  recovery.

Primary collection buckets:

| Stage 1 bucket | First-release target |
|---|---:|
| node/atomic programs | 26,000 |
| route/action combinations | 20,000 |
| high-motion and special traversal | 8,000 |
| weapon-state, environmental fire, and reload | 6,000 |
| Total | 60,000 |

Unless a table in this specification declares a non-uniform target, every
applicable categorical choice is scheduled approximately uniformly. The
manifest generator uses a deterministic balanced covering design rather than
independent random draws, but exact equality is not required. Planned cells
inside each applicable `dataset role x primary bucket` stratum target uniform
weight with up to 5% relative deviation from the ideal cell count. Realized
accepted distributions prefer a 10% relative envelope and may use a fixed
15% envelope for physical or realized marginals when authoritative
certification rejects make the joint 10% problem infeasible. Any larger
manifest-version exception must publish the conditioned feasibility bound,
use a fixed threshold declared before selection, and be recorded in manifest
metadata. Dynamically clamping a quota to the available pool, relabeling, or
capture-time fallback is prohibited. Small strata are audited for coverage
rather than percentage error.

Stage-1 v5 distinguishes certified-path selection from semantic-row
expansion. The selector uses the tighter 15% physical/realized envelope.
Because the no-weapon variants must remain unique across the nine held
weapons, each selected path contributes a hard-bounded 9-13 semantic rows
rather than silently duplicating a `(path, weapon, action)` tuple. The final
row-level audit therefore uses a fixed 20% physical/realized envelope and 15%
planned-enemy envelope. It also hard-checks the 9-13 weight bound, exact
role/bucket and weapon-action cells, every category, and the tighter
prototype-selection audit. These semantic envelopes are fixed for v5, not
computed from the observed manifest. Across each wave, mean absolute path
weight deviation from the ten-row center is at most 0.50; this prevents a
formally feasible solver from needlessly concentrating weight at 9 and 13.
The fixed-bound audit is
`stage1_path_certification_v5/feasibility/SEMANTIC_WEIGHT_CONSTRAINT_AUDIT.json`:
with the exact certified-path index and primary selection, 0.30 is proven
infeasible, 0.35 and 0.40 produced no feasible incumbent within the declared
solver budget, and 0.50 is the first audited feasible bound. A solver timeout
is not described as a proof of infeasibility. The manifest records the audit
hash and primary-selection hash; changing the index, selection, generator, or
audit implementation invalidates that authorization rather than selecting a
different runtime distribution.

The Stage-1 action axes are:

- locomotion direction: `idle`, forward, backward, left, right,
  forward-left, forward-right, backward-left, and backward-right;
- view direction: stationary, yaw-left, yaw-right, pitch-up, pitch-down, and
  the four yaw-sign x pitch-sign diagonals;
- dynamic temporal profile: full-clip sustained, early hold/release,
  middle-window, late onset/hold, two-pulse, stop-and-go, reversal, and
  eased variable-rate;
- action arity where applicable: atomic, pairwise, and three-way;
- all nine held weapon models, independent of locomotion, view, map, role,
  and motion bin.

Movement and view inputs are continuous, not categorical one-hot controls.
Direction labels constrain signs and coverage, while every active non-route
stratum spreads candidate magnitudes through a continuous interval. Initial
movement-magnitude proposal intervals are `[0.10,0.30]`, `[0.25,0.50]`,
`[0.45,0.70]`, `[0.65,0.90]`, and `[0.85,1.00]` for the five ordered
net-displacement target bins; high-motion candidates use `[0.85,1.00]`.
These are candidate-generation priors, not realized-bin labels. Route actions
retain their continuously varying calibrated usercmd values. Realized
telemetry and certification decide the final motion bin.

Yaw-amplitude proposals are continuously spread inside `0.5-14`, `17-43`,
`48-87`, `96-175`, and `185-260` degrees for the five yaw-range targets.
Pitch-amplitude proposals use `0.5-4.5`, `6-14`, `16-29`, and `32-60`
degrees. The temporal profile converts these amplitudes to per-frame
continuous right-stick values; source values outside the global normalized
contract hard-fail instead of being clipped into range.

Direction signs remain balanced inside every amplitude bin. Temporal profiles
apply separately to locomotion and view when that axis is active. In
particular, no profile may be implemented by consuming the hidden warm-up,
every late-onset profile acts during output ticks 160-319, and constant-rate
monotonic camera sweeps are at most one of the eight equally scheduled view
profiles. A fixed world-space movement heading combined with a monotonic
camera turn may not be used as the dominant construction because it
systematically creates circular-looking trajectories.

Stage 1 targets approximately 15,000 episodes with a weapon input, crossed
with the other primary buckets rather than confined to the 6,000 dedicated
weapon rows:

| Weapon input | Stage-1 count | No enemy | Enemy distractor |
|---|---:|---:|---:|
| environmental primary | 10,000 | 7,500 | 2,500 |
| successful reload | 4,950 | 3,750 | 1,200 |

The 6,000 `weapon-state, environmental fire, and reload` rows target about
4,000 primary-fire and 1,950 successful-reload inputs, with 50 no-weapon
variants required by the safe-fire eligibility boundary; the remaining
approximately 9,000 are balanced action overlays in the other three primary
buckets. Primary fire is approximately uniform over all nine weapons. Reload
is approximately uniform over the eight reloadable weapons. Stage 1 schedules
no secondary-fire input and requires `LT=0` in every emitted model-action row.
Enemy-distractor fire additionally requires the target to be outside the shot
path and authoritative zero-target-damage proof.

The enemy-distractor/weapon-environment cell is fixed at 1,000 primary-fire,
450 reload, and 50 no-weapon rows. Only 133 of its 184 certified-pool paths
have an admitted safe-fire relation; an unsafe path can contribute at most
eight distinct reload variants. The 50 no-weapon rows therefore preserve the
9-13 unique-row bound without reducing the 1,000 fire examples or inventing a
runtime action substitute.

Movement amplitude is assigned from realized authoritative telemetry, not from
the action-program name. Net displacement, maximum displacement from the reset
origin, 3D/XY path length, speed P95/max, and vertical range are logged
separately. The initial Stage 1 net-displacement marginal is:

| Realized 5-second net displacement | Target |
|---|---:|
| `<64` units | 15% |
| `64-256` units | 20% |
| `256-512` units | 25% |
| `512-1024` units | 25% |
| `>1024` units | 15% |

The nominal design target is at least 30% with path length `>=1000` units and
at least 10% with path length `>=2000` units. For the immutable Stage-1 v5
certificate index only, the fixed certified-path selection floors are 25%
and 9%, respectively; after the bounded 9-13 semantic expansion, the formal
row floors are 24.5% and 9%. The joint net-`>=512`/yaw-`>=90` floor is 10% at
path selection and 9% at final-row audit. Under the other locked role/bucket, physical,
realized-motion, joint-motion, collision, and map constraints, the exact
v5-pool maxima are 1,543/6,000 (25.72%) and 573/6,000 (9.55%); therefore the
nominal pair is jointly infeasible. This is an audited certificate-pool
exception, not a dynamic capacity clamp, and later certificate indexes return
to the nominal target unless they publish a new feasibility audit. A long
path with low maximum displacement is a high-local-motion example; it does
not satisfy a large-displacement quota.

The Stage-1 v5 12,000-row replenishment file is a deficit reserve, not a
second independently balanced release and not an instruction to launch all
12,000 rows. It is generated only after primary selection from the remaining
immutable certified pool, with this fixed pre-selection residual policy:

| Role / primary bucket | Reserve rows |
|---|---:|
| no enemy / node atomic | 3,930 |
| enemy distractor / node atomic | 1,270 |
| no enemy / route action | 3,000 |
| enemy distractor / route action | 1,000 |
| no enemy / high motion | 1,270 |
| enemy distractor / high motion | 330 |
| no enemy / weapon environment | 900 |
| enemy distractor / weapon environment | 300 |

Within those fixed cells, semantic expansion targets 1,978 environmental
primary-fire rows, 1,001 successful-reload rows, and 9,021 rows without a
weapon input. The enemy-distractor/weapon-environment cell is fixed at
180 fire, 100 reload, and 20 no-weapon rows: its residual pool can provide 21
safe fire-eligible paths, while 200 unique fire variants would require at
least 23. This is a declared action-cell policy and is checked as a path-level
capacity constraint before semantic expansion. Enemy relation, distance, and policy use their declared residual
targets with a fixed 5% envelope; requiring all three marginals exactly is
jointly infeasible even though each exact marginal is feasible alone.

The fixed residual net-displacement admission counts are 180, 1, 222, 594,
and 203 certified paths in ascending bin order. Their nominal semantic-row
centers are 1,800, 10, 2,220, 5,940, and 2,030 and use the fixed v5 semantic
row envelope above.
They are the optimal minimum-weighted-relative-deviation solution after
locking the cell, long-path, joint-motion, yaw/pitch, collision, map, and
category-coverage gates. In particular, only one certified residual prototype
in the `64-256` bin can participate in the joint design after the primary
wave. The design-time feasibility audit records the failed constraint
combinations, the unclamped optimization, and its exact certificate-index
hash. Physical marginals use the same fixed 15% envelope around the published
optimized residual targets; every locomotion direction, view direction,
temporal profile, and jump state remains covered.

The exact 1,200-path optimized physical centers are:

- locomotion: each of the eight compass directions 89, idle 88, and
  route-follow 400;
- movement profile: stop-and-go 53, late-onset 53, sustained 382,
  middle-window 89, two-pulse 53, early-release 74, eased 48,
  route-calibrated 400, and reversal 48;
- view direction: pitch-up 70, yaw-left/pitch-down 130, yaw-right 147,
  yaw-right/pitch-up 329, yaw-left 175, yaw-right/pitch-down 133,
  yaw-left/pitch-up 122, pitch-down 76, and stationary 18;
- view profile: reversal 112, middle-window 117, two-pulse 117,
  early-release 380, late-onset 108, sustained 97, eased 119, and
  stop-and-go 150;
- jump false 995 and true 205.

Each role/bucket cell also requires enough physical-action-arity-`<=2`
certified paths to support its fixed 9-13 unique semantic-row weight. This
capacity is solved before expansion and is part of the immutable
replenishment feasibility audit. Fire, reload, and no-weapon counts are
allocated together by one deterministic integer program per cell; separate
greedy passes, observed-capacity clamps, duplicate semantic tuples, and
capture-time substitution are prohibited.

This manifest-version exception is declared and audited before formal
selection; it is not a capacity clamp computed inside the final solver. The
reserve may be launched only after the global primary audit names deficient
cells, and only matching reserve rows may be selected. The final admitted
dataset is audited globally; unused reserve rows remain non-training
candidates.

Camera amplitude is also assigned from realized camera telemetry. Log
unwrapped yaw range, yaw total variation, yaw net change, largest monotonic
turn, maximum per-frame turn, pitch range, and pitch total variation. The
initial Stage 1 yaw-range marginal is:

| Realized yaw range | Target |
|---|---:|
| `<15 deg` | 30% |
| `15-45 deg` | 25% |
| `45-90 deg` | 15% |
| `90-180 deg` | 20% |
| `>=180 deg` | 10% |

Pitch range targets are `<5 deg` 45%, `5-15 deg` 25%, `15-30 deg` 20%, and
`>=30 deg` 10%. At least 10% of Stage 1 must jointly realize net displacement
`>=512` units and yaw range `>=90 deg`. Small-angle oscillation may contribute
to total variation but may never satisfy a large-range bucket.

The 75% no-enemy / 25% enemy-distractor ratio is enforced within action,
weapon, map, and motion strata where feasible, not only as a global marginal.
No action may be deterministically bound to a weapon model.

### 4.2 `foundation_no_enemy`

The enemy entity must truly be absent. Hiding a spawned enemy outside the view
does not satisfy this role.

Route generation uses the 3,241 base-map waypoints found in the pinned
official map archive as privileged waypoint/connection data:

```text
validated waypoint graph
-> coverage-driven route selection
-> authoritative 64 Hz calibration controller
-> frozen 384-tick usercmd schedule
-> reset and deterministic replay
-> demo, offline render, encode, QA
```

The calibration pass is not training data. The formal replay remains a
pre-generated, auditable engine-usercmd sequence.

Each five-second episode covers a local route of approximately 500-1400 engine
units. Dataset-level graph coverage, not a single episode, covers the map.

Initial view-policy target:

| View policy | Target |
|---|---:|
| look along route | 50% |
| scan while following | 30% |
| junction/vertical-feature view | 15% |
| rapid turn/look back/large pitch | 5% |

### 4.3 `foundation_enemy_distractor`

The enemy is a visual/audio distractor, not an aim target:

- the enemy never attacks;
- the player policy does not target the enemy;
- no player/enemy damage or physical collision is allowed;
- the player may continue locomotion, view, jump, primary-fire, or reload
  actions; weapon selection remains absent;
- environmental fire is allowed only when the target is outside the shot path
  and authoritative telemetry proves zero target damage;
- enemy world motion is frozen before replay and never reads the crosshair,
  camera pose, or live aim action.

Actual screen-relation targets across 15,000 episodes:

| Actual target relation | Definition | Target | Count |
|---|---|---:|---:|
| offscreen/fully occluded | no valid visible output frames | 25% | 3,750 |
| visible, far from crosshair | angular error always >10 deg | 30% | 4,500 |
| near crosshair | minimum error 3-10 deg, never centered | 20% | 3,000 |
| brief center pass | <=3 deg for 1-20% of output frames | 15% | 2,250 |
| center linger | <=3 deg for 20-80% of output frames | 7% | 1,050 |
| nearly continuous center | <=3 deg for >=80% of output frames | 3% | 450 |

Enemy distance is crossed with screen relation rather than inferred from it.
`visible_far` means far from the crosshair, not physically far away. The
Stage 1 enemy-distractor distance marginal is:

| Distance bin | Target | Count |
|---|---:|---:|
| close, `64-256` units | 25% | 3,750 |
| near, `256-512` units | 30% | 4,500 |
| medium, `512-768` units | 25% | 3,750 |
| far, `768-1024` units | 12% | 1,800 |
| very far, `1024-1536` units | 6% | 900 |
| extreme, `>1536` units | 2% | 300 |

Close plus near must remain at least 50% globally and within major
map/appearance/action strata; far plus very-far plus extreme has a hard maximum
of 25%. Close placement must still pass hull-clearance, no-collision, LOS, and
screen-size gates.

`centered` requires render visibility, authoritative LOS, and angular error
`<=3 deg`. Approximately 11,250 episodes have a meaningfully visible enemy,
6,750 reach the crosshair vicinity, and 3,750 become centered at least briefly.

Initial-centered episodes remain capped at 10-15%. A continuously centered
enemy may not be implemented by camera-relative enemy motion. Such examples
must arise from static/independent world motion and an appropriate camera/route
segment.

Primary/secondary attack while a visible target is centered or intentionally
aimed at the target belongs to Stage 2, even if the shot misses.

## 5. Stage 2: causal interaction

### 5.1 Learning objective

Stage 2 teaches the temporal chain:

```text
target appears
-> observation/detection
-> yaw/pitch response
-> acquire, track, lose, or reacquire
-> primary fire or deliberate no-fire
-> projectile/impact
-> miss, damage, or death
```

The model-facing player action uses continuous `j_left.x/j_left.y` and
`j_right.x/j_right.y` values in `[-1,1]`; primary fire and all other buttons
are binary. Secondary fire, reload, weapon selection, and zoom/ADS are fixed
to zero in Stage 2.

Target-conditioned aim is generated from manifest-frozen analytic player and
enemy trajectories. Stochastic aim does not read target, player, camera, or
crosshair state. Both policies, route/locomotion, enemy world trajectory, and
the final applied usercmd are separately logged. Retry never resamples an
action program.

### 5.2 Aim-policy marginal

The formal manifest is generated from four approximately balanced families.
Sub-arms are approximately uniform within each family except for the
pre-registered weapon-rate calibration described below.

| Aim family | Approximate target | 40k guide |
|---|---:|---:|
| visible target, no primary fire | 15% | 6,000 |
| stable, overshoot-correct, or predictive tracking | 30% | 12,000 |
| edge-graze or near-miss humanized tracking | 30% | 12,000 |
| stochastic local or broad aim with random primary fire | 25% | 10,000 |

Target-conditioned tracking must retain bounded acceleration, residual bias,
micro-corrections, lag, and probabilistic overshoot/correction; it may not
hard-lock the crosshair. Edge/near-miss offset direction and magnitude vary
across episodes. Stochastic aim and fire remain useful even when they happen
to hit: authoritative telemetry, not intent, supplies the target outcome.

### 5.3 Actual outcome marginal

The episode-level guide is deliberately not majority-positive:

| Authoritative target outcome | Approximate target | 40k guide |
|---|---:|---:|
| no fire | 15% | 6,000 |
| fired but no target damage | 40% | 16,000 |
| hit and target survives | 35% | 14,000 |
| kill | 10% | 4,000 |

In addition, every authoritative fire event receives a target-specific label.
The approximate per-fire target-hit bands are:

| Weapon | Target-hit band |
|---|---:|
| Blaster | 35-45% |
| Shotgun | 45-55% |
| MachineGun | 30-40% |
| Mortar | 30-40% |
| Electro | 35-45% |
| Crylink | 40-50% |
| Vortex | 30-40% |
| Hagar | 30-40% |
| Devastator | 35-45% |

These are approximate batch-level bands; up to five percentage points of
sampling deviation is acceptable. A target hit means authoritative damage to
the declared enemy entity, resolved through the event parent graph to that
fire. Self-damage, unrelated damage, world impact, and mere crosshair overlap
are not target hits. Direct, splash, and pellet mechanisms are recorded
separately.

The manifest's weapon-conditioned arm weights and frozen offset parameters
must produce these rates naturally. Realized outcome is never an individual
episode admission or replacement gate. If an accepted batch misses a weapon
band, only a new immutable future manifest may change that weapon stratum's
arm weights or frozen parameters. Selecting individual episodes because they
hit or missed is forbidden.

Each `shot_outcomes.parquet` row must include the declared target entity,
target hit/outcome, target damage, direct/splash/pellet mechanism, observation
completeness, and right-censor status. Projectile negatives require at least
96 authoritative ticks after fire. Formal training requires
`target_observation_complete=true` and `right_censored=false` for every fire.

### 5.4 Distance marginal

The primary measure is `distance_at_fire`; no-fire examples use a declared
reference tick.

| Distance bin | 3D engine-unit distance | Target |
|---|---:|---:|
| close | 64-256 | 25% |
| near | 256-512 | 30% |
| medium | 512-768 | 25% |
| far | 768-1024 | 12% |
| very far | 1024-1536 | 6% |
| extreme | >1536 | 2% |

Also record reset/reference/fire/impact/damage distance, episode min/max,
horizontal distance, vertical delta, closing/stable/opening, LOS/occlusion,
projected target size, target bearing, and crosshair angular error.

Across Stage 2, close plus near must remain at least 50%, with a 55% target.
Far plus very-far plus extreme must remain at or below 25%, with a 20% target.
The constraint is audited across weapon, outcome, aim policy, map, appearance,
and player-motion strata so long-range cases cannot dominate a visually
convenient subset.

Every weapon must retain all physically feasible distance and outcome bins.

### 5.5 Required interaction axes

- nine core weapons with primary fire and deliberate no-fire;
- seven core models and two official skins;
- stationary, lateral, approach, retreat, and stop-and-go target motion;
- stationary, moving, jumping, and tracking player motion;
- no-fire, miss, hit-survive, and kill;
- zero, low, partial, and full hit-rate bands;
- direct, splash, and pellet mechanisms where applicable;
- clear, partial, and blocked LOS;
- relative height and screen quadrant;
- initial acquisition, loss, and reacquisition.

Use a constrained covering design over high-priority pairs and selected triples;
do not materialize the full Cartesian product.

## 6. Enemy-crosshair bias controls

The principal control is the realized joint distribution across all
enemy-present data.

Definitions:

```text
centered = render_visible AND authoritative_LOS AND angular_error <= 3 deg
continuous = condition holds for >=80% of output frames
```

Hard distribution gates:

- initial-centered enemy-present episodes: at most 10-15%;
- Stage 1 continuous-centered episodes: at most 3% target, hard maximum 5%;
- Stage 2 continuous-visible and continuous-centered episodes: at most 10%;
- every map/distance/motion stratum must cover screen quadrants, peripheral,
  near, centered, enter-FOV, exit-FOV, intermittent, and occluded conditions
  where physically feasible;
- no model, skin, weapon, distance, or outcome may be deterministically tied to
  centered or visible status;
- enemy world motion never reads crosshair/camera input;
- target alignment after an explicit yaw/pitch aim response is valid desired
  causality and must not be decorrelated away.

Matched counterfactual groups may reuse one route or enemy world trajectory
with no-response, delayed, tracking, or offset-aim variants. Every member of a
group must be assigned to the same train/validation/test split.

## 7. Map-exploration policy and QA

Waypoint nodes and connections are validated live for hull clearance, ground,
reachable component, vertical class, special traversal, and void risk.

The calibration controller operates at the authoritative tick:

1. locate the player on the planned route;
2. select a one/two-node lookahead;
3. compute desired world-space velocity;
4. project it onto current camera forward/right axes;
5. produce forward/strafe and bounded view deltas;
6. trigger jump only for a route edge or explicit action program;
7. reject stalled, diverged, void, death, or unintended-teleport runs;
8. freeze the successful 384-tick action schedule.

Route acceptance:

- route progress >=85%;
- waypoint reach rate >=90%;
- cross-track error P95 <=96 units;
- no-progress interval <=0.5 seconds;
- no unintended death, void, stuck state, or teleport;
- every frame maps to a route segment and authoritative state;
- calibration/frozen replay remain within declared tolerance;
- same route/seed/actions yield the same authoritative telemetry hash.

## 8. Episode artifact contract

Every accepted v2 episode contains:

- `episode.json`
- `video.mkv`
- `actions.parquet`
- `model_actions.parquet`
- `states.parquet`
- `events.parquet`
- `frames.parquet`
- `audio_events.parquet`
- `target_relations.parquet`
- `qa.json`

Route-driven episodes additionally contain:

- `route_plan.json`
- `route_trace.parquet`
- `base_actions.parquet`
- `aim_overlay.parquet`

Namespaces:

- `actions.parquet`: desired/sent/applied engine usercmd, never raw HID;
- `model_actions.parquet`: 320 frame-aligned LTX-2 CrossFPS rows with
  `j_left`, `j_right`, and binary controller-button columns; every
  `source_action_tick` must equal the corresponding
  `frames.parquet.episode_server_tick`;
- `states.parquet`: canonical authoritative engine state;
- `events.parquet`: authoritative event graph;
- `frames.parquet`: camera, projection, renderer, PTS, and frame/tick mapping;
- `target_relations.parquet`: visibility, LOS, screen relation, angular error,
  distance, and interaction phase;
- route/controller/aim-overlay files: privileged collection metadata, excluded
  from default model inputs.

`episode.json` records at least `data_spec_sha256`, `dataset_role`,
`training_stage`, `map_region_id`, `route_group_id`,
`counterfactual_group_id`, `appearance_id`, `weapon`, `split`, build/source
commit, asset lock, and schema version.

## 9. Per-episode and dataset-level QA

Existing immutable media gates remain:

- exactly 320 decoded video frames;
- exactly 240,000 audio samples/channel;
- exact 750 samples/frame relation;
- frame-to-authoritative-tick success >=99.9%;
- exactly 320 normalized model-action rows, finite joystick values in
  `[-1,1]`, binary button values, exact frame/tick linkage, and a reversible
  match to the audited engine usercmd under the locked global scaling;
- non-silent audio and measured onset when interaction sound is expected;
- mixer-onset error <=2 ms;
- event linkage >=99.9%;
- every health/armor/ammo/clip/reserve change explained;
- renderer vendor and exact device identity explicitly recorded; the renderer
  must be NVIDIA hardware, while the particular NVIDIA generation is not
  fixed; llvmpipe, softpipe, and other software renderers are forbidden;
- every frame has the locked FOV90 frustum and finite projection values;
- no forbidden HUD/audio/assets;
- deterministic authoritative telemetry for same seed/actions;
- every declared reload example proves one linked start/complete pair, exact
  weapon/actor/timing, clip increase to capacity, and reserve decrease.

Additional v2 gates:

- no-enemy role has no enemy entity or enemy event;
- enemy-distractor role has no target damage, target-directed attack, collision,
  or enemy attack;
- hit-survive has damage and no death;
- kill has a linked death;
- target relation is re-derived from authoritative state and render telemetry;
- route and screen-relation bins are assigned from realized telemetry;
- model/skin/color rendered identity matches the scenario;
- weapon-specific causal event rules pass;
- action x weapon x map x region and appearance x screen-relation coverage are
  audited globally;
- background/route/encounter repetition is capped.

RGB bit identity across different GPU-driver versions remains out of scope.

## 10. Split policy

Canonical manifests:

- `foundation_no_enemy`
- `foundation_enemy_distractor`
- `causal_interaction`

The split unit is at least:

```text
map + region + route/encounter geometry + counterfactual group
```

Random episode splitting is forbidden. The final release provides both
held-out-region evaluation on seen maps and whole-map OOD evaluation. Exact
held-out maps are frozen only after all-map preflight.

Legacy `split=pilot`, `split=map_preflight`, `split=v2_coverage_pilot`,
`split=v2_motion_distance_pilot`, and `split=v2_stage1_review_fov90` are
permanently excluded from training.

## 11. Formal storage policy

- Preserve all legacy Pilot raw data.
- Formal accepted raw AVI is bounded temporary staging.
- After encode, QA, SHA256, and atomic publication succeed, delete temporary
  raw AVI.
- Preserve all reject raw and a stratified 1-5% accepted raw audit sample.
- Keep final MKV, demo, telemetry, QA, logs, manifests, source/asset locks, and
  checksums for every accepted episode.
- Reserve approximately 3-5 TiB for the first 100k release.

## 12. Admission work before formal collection

The following are non-training bounded validation sets:

1. `all_map_preflight`: all 29 maps, four spatial probes/map when feasible.
2. `v2_coverage_pilot`: a small accepted set covering every high-level Stage 1
   and Stage 2 category plus all nine weapons and all 14 core appearances.
3. `v2_motion_distance_pilot`: a bounded supplement that proves large
   displacement, 90/180/360-degree yaw, large pitch, joint
   translation/rotation, and a close/near-heavy enemy-distance mix using
   realized telemetry.
4. `v2_stage1_review_fov90`: a 60-episode, Stage-1-only review set sampled from
   the declared Stage 1 marginals after locking the corrected FOV90 camera
   intrinsics. It is review evidence, not training data or production
   authorization.
5. Per-map/per-weapon HTML previews, coverage tables, QA summary, rejects, and
   SHA256 manifest.

The coverage and motion/distance bounded sets have passed. None of these
bounded reports authorizes production collection. Stage 1 may be collected
only through a separately published immutable formal manifest, compatibility
audit, runtime-code lock, build lock, and readiness decision; Stage 2 requires
its own corresponding authorization.

## 13. Production-preflight admission tiers

Final distribution tables in this specification are dataset-level scheduling
and quota targets. They are not per-episode reasons to destroy technically
valid data.

The bounded `split=v2_stage1_production_preflight` uses the explicit
`acceptance_policy=tiered_review_v1` contract:

- hard capture-integrity failures reject the attempt;
- realized motion, view, enemy-relation, distance, and outcome labels are
  derived from authoritative/render telemetry;
- a mismatch against an intended scheduler cell is rebucketed and sent to
  human review rather than repeatedly rendered;
- role conflicts such as foundation damage remain excluded from automatic
  Stage 1 admission but are preserved for inspection;
- reload remains hard for every declared reloadable weapon and requires one
  linked start/complete pair, exact weapon/actor/timing, clip increase to
  capacity, and reserve decrease;
- human review decisions are append-only and do not alone authorize training;
- every preflight row remains `training_admitted=false`.

Operational retries must replay the same seed, geometry, and action sequence.
Only process/render/encode/incomplete-artifact failures are retryable.
Publication is exactly-once, refuses overwrite, records SHA256, and maintains
an append-only queue state log. The full decision table is defined in
`STAGE1_PRODUCTION_PREFLIGHT_POLICY.md`.
