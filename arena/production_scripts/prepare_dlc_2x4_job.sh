#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
duel_root=$(cd -- "$script_dir/.." && pwd -P)

if (($# < 2 || $# > 3)); then
  printf 'usage: %s TARGET_VIDEO_HOURS RUN_ID [DLC_JOB_NAME]\n' "$0" >&2
  exit 64
fi

target_hours=$1
run_id=$2
job_name=${3:-}
workspace_id=${PAI_WORKSPACE_ID:-89}
resource_id=${XONOTIC_DUEL_DLC_RESOURCE_ID:-quota114cy6id9sq}
worker_image=${XONOTIC_DUEL_DLC_IMAGE:-vivix-data-registry-vpc.ap-southeast-8.cr.aliyuncs.com/vivix/vivix_data:p02-turbo-torch212-cu130-fa4}
data_source_id=${XONOTIC_DUEL_DLC_DATA_SOURCE_ID:-d-bxl1kc01xrjyrds68a}
priority=${XONOTIC_DUEL_DLC_PRIORITY:-8}
accessibility=${XONOTIC_DUEL_DLC_ACCESSIBILITY:-PUBLIC}
lanes_per_gpu=${XONOTIC_DUEL_LANES_PER_GPU:-2}
production_base=${XONOTIC_DUEL_PRODUCTION_ROOT:-$duel_root/outputs/production_2x4}
spec_root=${XONOTIC_DUEL_SPEC_ROOT:-$duel_root/production_specs}

[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || { printf 'invalid RUN_ID: %s\n' "$run_id" >&2; exit 64; }
[[ "$workspace_id" =~ ^[0-9]+$ ]] || { printf 'invalid workspace id\n' >&2; exit 64; }
[[ "$priority" =~ ^[0-9]+$ ]] || { printf 'invalid priority\n' >&2; exit 64; }
case "$accessibility" in PUBLIC|PRIVATE) ;; *) printf 'accessibility must be PUBLIC or PRIVATE\n' >&2; exit 64 ;; esac
case "$lanes_per_gpu" in 1|2|4|8) ;; *) printf 'lanes per GPU must be 1, 2, 4, or 8\n' >&2; exit 64 ;; esac
[[ "$production_base" == /* && "$spec_root" == /* ]] || { printf 'output roots must be absolute\n' >&2; exit 64; }

total_episodes=$(python - "$target_hours" <<'PY'
from decimal import Decimal, InvalidOperation
import sys

try:
    hours = Decimal(sys.argv[1])
except InvalidOperation:
    raise SystemExit(2)
episodes = hours * 60
if hours <= 0 or episodes != episodes.to_integral_value():
    raise SystemExit(2)
print(int(episodes))
PY
) || {
  printf 'TARGET_VIDEO_HOURS must be positive and resolve to an integer number of 60-second episodes\n' >&2
  exit 64
}

if [[ -z "$job_name" ]]; then
  hours_tag=${target_hours//./p}
  job_name="xonotic_duel_v11_${hours_tag}h_2x4_$(date -u +%m%d)"
fi
[[ "$job_name" =~ ^[A-Za-z0-9._-]+$ ]] || { printf 'invalid DLC job name: %s\n' "$job_name" >&2; exit 64; }
(( ${#job_name} <= 63 )) || { printf 'DLC job name is longer than 63 characters\n' >&2; exit 64; }

job_root="$production_base/$run_id"
[[ ! -e "$job_root" ]] || {
  printf 'refusing a new spec because production output already exists: %s\n' "$job_root" >&2
  exit 73
}

mkdir -p "$spec_root"
spec_path="$spec_root/${run_id}_2x4.json"
[[ ! -e "$spec_path" ]] || { printf 'refusing to overwrite prepared spec: %s\n' "$spec_path" >&2; exit 73; }

user_command="cd $duel_root && export XONOTIC_DUEL_PRODUCTION_RUN_ID=$run_id XONOTIC_DUEL_TOTAL_EPISODES=$total_episodes XONOTIC_DUEL_EXPECTED_NODES=2 XONOTIC_DUEL_GPUS_PER_NODE=4 XONOTIC_DUEL_LANES_PER_GPU=$lanes_per_gpu XONOTIC_DUEL_PRODUCTION_ROOT=$production_base && exec bash production_scripts/launch_dlc_2x4_hold.sh"

spec_tmp="$spec_root/.${run_id}_2x4.$$.tmp"
jq -n \
  --arg name "$job_name" \
  --arg workspace_id "$workspace_id" \
  --arg resource_id "$resource_id" \
  --arg worker_image "$worker_image" \
  --arg data_source_id "$data_source_id" \
  --arg user_command "$user_command" \
  --arg accessibility "$accessibility" \
  --argjson priority "$priority" \
  '{
    Name:$name,
    WorkspaceId:$workspace_id,
    ResourceId:$resource_id,
    JobType:"PyTorchJob",
    Priority:$priority,
    Accessibility:$accessibility,
    JobSpecs:[{
      Type:"Worker",Image:$worker_image,PodCount:2,
      ResourceConfig:{CPU:"120",GPU:"4",Memory:"800Gi",SharedMemory:"800Gi"}
    }],
    DataSources:[{
      DataSourceId:$data_source_id,DataSourceType:"bmcpfs",DataSourceVersion:"v1",
      MountAccess:"RW",MountPath:"."
    }],
    UserCommand:$user_command
  }' >"$spec_tmp"
mv "$spec_tmp" "$spec_path"

jq -e \
  --arg name "$job_name" \
  --arg workspace_id "$workspace_id" \
  --arg resource_id "$resource_id" \
  --arg data_source_id "$data_source_id" \
  --arg run_id "$run_id" \
  --argjson total_episodes "$total_episodes" \
  '.Name==$name and .WorkspaceId==$workspace_id and .ResourceId==$resource_id and .JobType=="PyTorchJob" and .JobSpecs[0].PodCount==2 and .JobSpecs[0].ResourceConfig.GPU=="4" and .DataSources[0].DataSourceId==$data_source_id and (.UserCommand|contains($run_id)) and (.UserCommand|contains("XONOTIC_DUEL_TOTAL_EPISODES="+($total_episodes|tostring))) and (.UserCommand|contains("launch_dlc_2x4_hold.sh"))' \
  "$spec_path" >/dev/null

sha256sum "$spec_path" >"$spec_path.sha256"
printf -v q_job_name '%q' "$job_name"
printf -v q_workspace_id '%q' "$workspace_id"
printf -v q_resource_id '%q' "$resource_id"
printf -v q_priority '%q' "$priority"
printf -v q_accessibility '%q' "$accessibility"
printf -v q_worker_image '%q' "$worker_image"
printf -v q_data_source '%q' "$data_source_id:v1:.:"
printf -v q_user_command '%q' "$user_command"
submit_command="/etc/dsw/runtime/export_bin/dlc submit pytorchjob -r ap-southeast-8 -e pai-dlc.ap-southeast-8.aliyuncs.com -w $q_workspace_id -n $q_job_name --resource_id $q_resource_id --priority $q_priority --accessibility $q_accessibility --oversold_type ForbiddenQuotaOverSold --workers 2 --worker_cpu 120 --worker_gpu 4 --worker_memory 800Gi --worker_shared_memory 800Gi --worker_image $q_worker_image -d $q_data_source --advanced_settings HpnAffinity=TryBest --command $q_user_command"

printf 'prepared_only=true\n'
printf 'submitted=false\n'
printf 'run_id=%s\n' "$run_id"
printf 'target_video_hours=%s\n' "$target_hours"
printf 'total_episodes=%s\n' "$total_episodes"
printf 'topology=2_nodes_x_4_gpus_8_global_ranks\n'
printf 'lanes_per_gpu=%s\n' "$lanes_per_gpu"
printf 'spec=%s\n' "$spec_path"
printf 'production_root=%s\n' "$job_root"
printf 'submit_command=%s\n' "$submit_command"
printf 'hold_contract=all ranks hold after completion; preflight and repeated runtime failures also keep Pods alive for inspection\n'
