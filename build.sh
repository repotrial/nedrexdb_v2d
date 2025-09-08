#!/bin/bash

setup_db() {
    local db_type=$1
    local config_file=".$db_type"_config.toml

    if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | build.sh - Starting setup of $db_type DB"; fi

    # Handle DB updates
    if [[ "$SKIP_UPDATE" == "1" ]]; then
       ./build.py restart-live --conf "$config_file"
    else
        local build_args=(update --conf "$config_file")

        if [[ "$DOWNLOAD_ON_STARTUP" == "1" ]]; then

          # update incl. metadata when setting download flag
          if [[ "$db_type" == "licensed" ]]; then
              build_args+=(--download)

           # when only building open db, download flag must be set
          elif [[ "$db_type" == "open" ]]; then
              if [[ "$SKIP_LICENSED" == "1" ]]; then
                build_args+=(--download)
              else
                build_args+=(--version_update .licensed_config.toml)
              fi

          fi
        # set versions anyways when no download
        else
          build_args+=(--version_update true)

        fi

        if [[ "$CREATE_EMBEDDINGS" == "1" ]]; then
          build_args+=(--create_embeddings)
        fi
        if [[ "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | DEBUG | build.sh - Running build with command: ./build.py ${build_args[@]}"; fi
        ./build.py "${build_args[@]}"
    fi

    # Clean volumes if not skipped
    if [[ "$SKIP_CLEAN" != "1" ]]; then
        if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | build.sh -Cleaning unused nedrex volumes"; fi
        ./clean_volumes.sh "$db_type"
    else
        if [[ "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | DEBUG | build.sh - Skipping clean"; fi
    fi

    if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | build.sh - Finished setup of $db_type DB"; fi
}

# Setup licensed DB if not skipped
[[ "$SKIP_LICENSED" != "1" ]] &&  setup_db licensed
# Setup open DB if not skipped
[[ "$SKIP_OPEN" != "1" ]] && setup_db open