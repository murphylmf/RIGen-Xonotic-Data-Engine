#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
release_id=stage2_long60_multi_enemy_ref42_multimap_hitscan_collision_camera_30h_20260829_v8
collection_root=./rigen_data/$release_id
dlc=${DLC_BIN:-/etc/dsw/runtime/export_bin/dlc}
region=${DLC_REGION:-ap-southeast-8}
endpoint=${DLC_ENDPOINT:-pai-dlc.ap-southeast-8.aliyuncs.com}
workspace_id=${PAI_WORKSPACE_ID:?PAI_WORKSPACE_ID is required}
resource_id=${LONG60_DLC_RESOURCE_ID:-quota114cy6id9sq}
data_source=${LONG60_DLC_DATA_SOURCE:-d-bxl1kc01xrjyrds68a:v1:.}
image=${LONG60_DLC_IMAGE:-vivix-data-registry-vpc.ap-southeast-8.cr.aliyuncs.com/vivix/vivix_data:p02-turbo-torch212-cu130-fa4}
job_name=${LONG60_DLC_JOB_NAME:-xonotic_long60_ref42_v8_frozen1791_4x4_hold_0829}

[[ -x "$script_dir/hold_long60_v8_frozen_4x4_node.sh" &&
   -r "$collection_root/control/FROZEN.json" &&
   -r "$collection_root/FROZEN_ACCEPTED.jsonl" ]] || {
  echo "frozen collection or hold entrypoint missing" >&2
  exit 66
}

task_command="bash -lc 'export PATH=./environment:\$PATH; export LONG60_COLLECTION_ROOT=$collection_root LONG60_EXPECTED_ACCEPTED=1791 LONG60_HOLD_RUN_ID=$job_name; exec bash $script_dir/hold_long60_v8_frozen_4x4_node.sh'"
args=(
  "$dlc" submit pytorchjob
  --ignore_local_config
  --name "$job_name"
  --workspace_id "$workspace_id"
  --resource_id "$resource_id"
  --data_sources "$data_source"
  --masters 1
  --workers 3
  --master_gpu 4
  --worker_gpu 4
  --master_cpu 120
  --worker_cpu 120
  --master_memory 800Gi
  --worker_memory 800Gi
  --master_shared_memory 800Gi
  --worker_shared_memory 800Gi
  --master_image "$image"
  --worker_image "$image"
  --command "$task_command"
  --priority 8
  --oversold_type ForbiddenQuotaOverSold
  --advanced_settings HpnAffinity=TryBest
  --aimaster_args '--job-execution-mode=Sync --enable-job-restart=True --max-num-of-job-restart=1000000 --enable-job-hang-detection=False --fault-tolerant-policy=OnFailure'
  --tags "Purpose=long60-frozen-hold,Topology=4x4-whole-node,Release=$release_id,FrozenAccepted=1791,Completion=hold-gpus"
  --accessibility PRIVATE
  -r "$region"
  -e "$endpoint"
)

echo "job_name=$job_name"
echo "topology=4_nodes_x_4_gpus_whole_node"
echo "frozen_accepted=1791"
echo "task_command=$task_command"
if [[ ${LONG60_DLC_DRY_RUN:-0} == 1 ]]; then
  printf 'dry_run_command='
  printf '%q ' "${args[@]}"
  printf '\n'
  exit 0
fi
exec "${args[@]}"
