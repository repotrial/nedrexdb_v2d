#!/bin/bash

echo "Starting setup of licensed DB"
./setup_data.sh /data/nedrex_files; ./build.py update --conf .licensed_config.toml --download
#./build.py update --conf .licensed_config.toml
./set_metadata.py --config .licensed_config.toml --version live
./clean_volumes.sh licensed
echo "Finished setup of licensed DB"

echo "Starting setup of open DB"
./build.py update --conf .open_config.toml
./set_metadata.py --config .open_config.toml --version live
./clean_volumes.sh open
echo "Finished setup of open DB"
