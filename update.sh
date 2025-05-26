#!/usr/bin/bash

export PATH="/opt/conda/bin:${PATH}"
echo $PATH
if [[ "$AUTOUPDATE" != "0" ]]; then
  export SKIP_UPDATE=0
fi
./build.sh
