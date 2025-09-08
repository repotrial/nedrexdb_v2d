#!/usr/bin/env bash
NEDREX_FILES=$1
DOWNLOADS=$NEDREX_FILES/nedrex_data/downloads

mkdir -p $DOWNLOADS
cd $DOWNLOADS
wget https://cloud.uni-hamburg.de/s/RiAtjZC3bb7bg7n/download/bioontology.zip -q -O bioontology.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded bioontology.zip"; fi
wget https://cloud.uni-hamburg.de/s/5meqDbTbgydo6Tj/download/drugbank.zip -q -O drugbank.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded drugbank.zip"; fi
wget https://cloud.uni-hamburg.de/public.php/dav/files/9wNb5HWL7RBH6ng/?accept=zip -q -O disgenet.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded disgenet.zip"; fi
wget https://cloud.uni-hamburg.de/s/PxWXAMY5bfS3ZcA/download/repotrial.zip -q -O repotrial.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded repotrial.zip"; fi
wget https://cloud.uni-hamburg.de/public.php/dav/files/SXmWg6Q7aLEkdf6/?accept=zip -q -O hippie.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded hippie.zip"; fi;
wget https://cloud.uni-hamburg.de/public.php/dav/files/WepcTz56PsNNa4P/?accept=zip -q -O sider.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded sider.zip"; fi
wget -nv https://zenodo.org/records/12806709/files/cosmic.zip?download=1 -q -O cosmic.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded cosmic.zip"; fi
wget -nv https://zenodo.org/records/12806709/files/intogen.zip?download=1 -q -O intogen.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded intogen.zip"; fi
wget -nv https://zenodo.org/records/12806709/files/ncg.zip?download=1 -q -O ncg.zip
if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Downloaded ncg.zip"; fi

for file in *.zip; do
    if [[ "$LOG_LEVEL" == "INFO" || "$LOG_LEVEL" == "DEBUG" ]]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | setup_data.sh - Unzipping $file..."
    fi
    unzip -qo "$file"
    rm -rf "$file"
done
cd ../../
mkdir -p nedrex_api/static
cd nedrex_api/static
wget https://cloud.uni-hamburg.de/s/PdXPnX77QpWzX7z/download -q -O static.zip
if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') | DEBUG | setup_data.sh - Downloaded static.zip"
fi
unzip -qo static.zip
if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') | DEBUG | setup_data.sh - Unzipped static.zip"
fi
mv static/* .
rm -rf static
rm -rf static.zip
