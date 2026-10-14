#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XONOTIC_CAPTURE_ROOT:-$(cd -- "$script_dir/.." && pwd -P)}
RELEASE_ID=${LONG60_RELEASE_ID:-stage2_long60_multi_enemy_lifecycle_30h_20260824_v2}
production_script=${LONG60_PRODUCTION_SCRIPT:-pilot_scripts/long60_production_v1.py}
build_tag=${LONG60_BUILD_TAG:-capture-65a48cd4a2c6-aarch64}
dlc=${DLC_BIN:-/etc/dsw/runtime/export_bin/dlc}
region=${DLC_REGION:-ap-southeast-8}
endpoint=${DLC_ENDPOINT:-pai-dlc.ap-southeast-8.aliyuncs.com}
workspace_id=${PAI_WORKSPACE_ID:?PAI_WORKSPACE_ID is required}
resource_id=${LONG60_DLC_RESOURCE_ID:-quota114cy6id9sq}
data_source=${LONG60_DLC_DATA_SOURCE:-d-bxl1kc01xrjyrds68a:v1:.}
image=${LONG60_DLC_IMAGE:-vivix-data-registry-vpc.ap-southeast-8.cr.aliyuncs.com/vivix/vivix_data:p02-turbo-torch212-cu130-fa4}
job_name=${LONG60_DLC_JOB_NAME:-xonotic_long60_multi30h_lifecycle_v2_2x4_hold_0824}
node_count=${LONG60_DLC_NODE_COUNT:-2}
case "$node_count" in
  2) worker_count=1 ;;
  4) worker_count=3 ;;
  *)
    echo "LONG60_DLC_NODE_COUNT must be 2 or 4; got $node_count" >&2
    exit 64
    ;;
esac
manifest_root="$root/manifests/$RELEASE_ID"
output_root="./rigen_data/$RELEASE_ID"

python_bin=./environment
[[ -x "$python_bin" && -r "$manifest_root/PREPARED.json" &&
   -r "$root/$production_script" &&
   -x "$root/build/$build_tag/bin/xonotic-local-sdl" ]] || {
  echo "prepared runtime or manifest missing" >&2
  exit 66
}
"$python_bin" "$root/$production_script" audit \
  --manifest-root "$manifest_root" \
  --output-root "$output_root"

task_command="bash -lc 'export PATH=./environment:\$PATH; cd $root; export LONG60_RUN_ID=$job_name LONG60_NODE_COUNT=$node_count LONG60_RELEASE_ID=$RELEASE_ID LONG60_PRODUCTION_SCRIPT=$production_script LONG60_BUILD_TAG=$build_tag LONG60_MANIFEST_ROOT=$manifest_root LONG60_OUTPUT_ROOT=$output_root; exec bash scripts/run_long60_production_2x4_node.sh'"
args=(
  "$dlc" submit pytorchjob
  --ignore_local_config
  --name "$job_name"
  --workspace_id "$workspace_id"
  --resource_id "$resource_id"
  --data_sources "$data_source"
  --masters 1
  --workers "$worker_count"
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
  --aimaster_args '--job-execution-mode=Sync --enable-job-restart=True --max-num-of-job-restart=10 --enable-job-hang-detection=False --fault-tolerant-policy=OnFailure'
  --tags "Purpose=long60-production-hold,Topology=${node_count}x4-whole-node,Release=$RELEASE_ID,RawAVI=disabled,Completion=hold-gpus"
  --accessibility PRIVATE
  -r "$region"
  -e "$endpoint"
)

echo "job_name=$job_name"
echo "topology=${node_count}_nodes_x_4_gpus_whole_node"
echo "raw_avi_retained=false"
echo "completion_policy=hold_gpus"
echo "task_command=$task_command"
if [[ ${LONG60_DLC_DRY_RUN:-0} == 1 ]]; then
  printf 'dry_run_command='
  printf '%q ' "${args[@]}"
  printf '\n'
  exit 0
fi
exec "${args[@]}"
