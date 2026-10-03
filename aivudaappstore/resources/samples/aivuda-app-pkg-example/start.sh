#!/usr/bin/env bash
set -e # exit on error

echo "[start.sh] started at $(date)"
echo "[start.sh] app: ${AIVUDA_APP_ID:-unknown}@${AIVUDA_APP_VERSION:-unknown}"


#-----------------------------------------------------------------
# Preparing aivuda app config parameters
#-----------------------------------------------------------------
source "${AIVUDA_APP_HELPERS_ENTRY_PATH}" # for aivuda_yaml_get()

planner_mode="$(aivuda_yaml_get 'robot.motion.planner.mode' '<missing>')"
max_speed="$(aivuda_yaml_get 'robot.motion.max_speed_mps' '<missing>')"
mission_profile="$(aivuda_yaml_get 'mission.profile.name' '<missing>')"

echo "[start.sh] config path: ${AIVUDA_APP_CONFIG_PATH:-<missing>}"
echo "[start.sh] planner mode: ${planner_mode}"
echo "[start.sh] max speed: ${max_speed}"
echo "[start.sh] mission profile: ${mission_profile}"


#-----------------------------------------------------------------
# Launch nodes
#-----------------------------------------------------------------
## your commands
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] heartbeat..."
  sleep 2
done
for i in {1..3}; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] heartbeat..."
  sleep 1
done



echo "[start.sh] finished at $(date '+%Y-%m-%d %H:%M:%S')"
