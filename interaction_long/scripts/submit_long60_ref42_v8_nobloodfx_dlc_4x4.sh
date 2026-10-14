#!/usr/bin/env bash


set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
source_release_id=stage2_long60_multi_enemy_ref42_multimap_hitscan_collision_camera_30h_20260829_v8
release_id=stage2_long60_multi_enemy_ref42_multimap_hitscan_collision_camera_30h_20260829_v8_nobloodfx_20260902_v1
production_script=pilot_scripts/long60_production_ref42_v8_collision_camera.py
build_tag=capture-3688c19201b0-aarch64
client_overlay=configs/capture_client_stage2_v19_no_blood_hitfx.cfg
manifest_root="$root/manifests/$source_release_id"
output_root="./rigen_data/$release_id"

dlc=${DLC_BIN:-/etc/dsw/runtime/export_bin/dlc}
region=${DLC_REGION:-ap-southeast-8}
endpoint=${DLC_ENDPOINT:-pai-dlc.ap-southeast-8.aliyuncs.com}
workspace_id=${PAI_WORKSPACE_ID:?PAI_WORKSPACE_ID is required}
resource_id=${LONG60_DLC_RESOURCE_ID:-quota114cy6id9sq}
data_source=${LONG60_DLC_DATA_SOURCE:-d-bxl1kc01xrjyrds68a:v1:.}
image=${LONG60_DLC_IMAGE:-vivix-data-registry-vpc.ap-southeast-8.cr.aliyuncs.com/vivix/vivix_data:p02-turbo-torch212-cu130-fa4}
job_name=${LONG60_DLC_JOB_NAME:-xonotic_long60_ref42_v8_nobloodfx_30h_4x4_hold_0902}
python_bin=./environment

[[ "$output_root" != "./rigen_data/$source_release_id" ]] || {
  echo "refusing to overwrite the source v8 collection" >&2
  exit 64
}
[[ -x "$python_bin" &&
   -r "$manifest_root/PREPARED.json" &&
   -r "$manifest_root/MANIFEST_METADATA.json" &&
   -r "$manifest_root/manifest.jsonl" &&
   -r "$root/$production_script" &&
   -r "$root/$client_overlay" &&
   -x "$root/build/$build_tag/bin/xonotic-local-sdl" ]] || {
  echo "prepared v8 runtime, manifest, or no-blood overlay missing" >&2
  exit 66
}

mkdir -p "$output_root/control"
printf '%s\n' \
  'release-local supervisor enabled: restart production after user-process exit and hold after completion' \
  > "$output_root/control/HOLD_ON_ABNORMAL_EXIT"

"$python_bin" "$root/$production_script" audit \
  --manifest-root "$manifest_root" \
  --output-root "$output_root"

task_command="bash -lc 'export PATH=./environment:\$PATH; cd $root; export LONG60_RUN_ID=$job_name LONG60_NODE_COUNT=4 LONG60_RELEASE_ID=$release_id LONG60_PRODUCTION_SCRIPT=$production_script LONG60_BUILD_TAG=$build_tag LONG60_MANIFEST_ROOT=$manifest_root LONG60_OUTPUT_ROOT=$output_root LONG60_MAX_NODE_PASSES=1000000 XONOTIC_CAPTURE_CLIENT_OVERLAY=$client_overlay; exec bash scripts/run_long60_production_2x4_node.sh'"
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
  --tags "Purpose=long60-nobloodfx-production-hold,Topology=4x4-whole-node,SourceRelease=$source_release_id,Release=$release_id,VisualFX=no-damageeffect-no-gibsplash,RawAVI=disabled,Completion=hold-gpus,AbnormalExit=supervised-restart-hold"
  --accessibility PRIVATE
  -r "$region"
  -e "$endpoint"
)

echo "job_name=$job_name"
echo "source_manifest=$manifest_root/manifest.jsonl"
echo "output_root=$output_root"
echo "topology=4_nodes_x_4_gpus_whole_node"
echo "client_overlay=$client_overlay"
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
