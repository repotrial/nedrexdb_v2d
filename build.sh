#!/bin/bash

setup_db() {
    local db_type=$1
    local config_file=".$db_type"_config.toml

    echo "Starting setup of $db_type DB"

    # Handle DB updates
    if [[ "$SKIP_UPDATE" == "1" ]]; then
        ./build.py restart-live --conf "$config_file"
    else
        local build_args=(update --conf "$config_file")
        if [[ "$DOWNLOAD_ON_STARTUP" == "1" && "$db_type" == "licensed" ]]; then
            build_args+=(--download)
        elif [[ "$DOWNLOAD_ON_STARTUP" == "1" && "$db_type" == "open" ]]; then
            build_args+=(--version_update)
        fi
        ./build.py "${build_args[@]}"
    fi

    # Clean volumes if not skipped
    if [[ "$SKIP_CLEAN" != "1" ]]; then
        ./clean_volumes.sh "$db_type"
    else
        echo "Skipping clean"
    fi

    echo "Finished setup of $db_type DB"
}


[[ "$DOWNLOAD_ON_STARTUP" == "1" ]] && echo "Download: ON" && ./setup_data.sh /data/nedrex_files

# Setup licensed DB if not skipped
[[ "$SKIP_LICENSED" != "1" ]] &&  setup_db licensed
# Setup open DB if not skipped
[[ "$SKIP_OPEN" != "1" ]] && setup_db open