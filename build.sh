#!/bin/bash

echo "Starting setup of licensed DB"
if [ "${DOWNLOAD_ON_STARTUP}" == "1" ]; then
     echo "Download: ON"
     ./setup_data.sh /data/nedrex_files; ./build.py update --conf .licensed_config.toml --download
  else
     echo "Download: OFF"
     if [ "${SKIP_UPDATE}" == "1" ]; then
       echo "only restarting"
       ./build.py restart-live --conf .licensed_config.toml
     else
       ./build.py update --conf .licensed_config.toml
       ./set_metadata.py --config .licensed_config.toml --version live
     fi
     if [ "${SKIP_CLEAN}" == "1" ]; then
        echo "Skipping clean"
      else
        ./clean_volumes.sh licensed
      fi
  fi

echo "Finished setup of licensed DB"


if [ "${SKIP_OPEN}" == "1" ]; then
  exit 0
fi
echo "Starting setup of open DB"
if [ "${SKIP_UPDATE}" == "1" ]; then
  ./build.py restart-live --conf .open_config.toml
else
  ./build.py update --conf .open_config.toml
  ./set_metadata.py --config .open_config.toml --version live
fi
if [ "${SKIP_CLEAN}" == "1" ]; then
  echo "Skipping clean"
else
  ./clean_volumes.sh open
fi
echo "Finished setup of open DB"
