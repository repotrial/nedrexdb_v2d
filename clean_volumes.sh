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
        echo "Removed unused volume: $volume"
    else
        echo "Volume is in use: $volume"
    fi
done