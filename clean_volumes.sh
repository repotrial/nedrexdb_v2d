#!/usr/bin/env bash
PREFIX=$1

# List all volumes with the specified prefix
volumes=$(docker volume ls --filter name=^${PREFIX} -q)

# Iterate through the list of volumes
for volume in $volumes; do
    # Check if the volume is in use
    if ! docker ps -a --filter volume=$volume -q | grep -q .; then
        # Remove the unused volume
        docker volume rm $volume
        if [[ "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | DEBUG | clean_volumes.sh - Removed unused volume: $volume"; fi
    else
        if [[ "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | DEBUG | clean_volumes.sh - Volume is in use: $volume"; fi
    fi
done