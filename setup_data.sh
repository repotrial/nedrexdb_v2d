#!/usr/bin/env bash
NEDREX_FILES=$1
DOWNLOADS=$NEDREX_FILES/nedrex_data/downloads

mkdir -p $DOWNLOADS
cd $DOWNLOADS
wget https://cloud.uni-hamburg.de/s/RiAtjZC3bb7bg7n/download/bioontology.zip -O bioontology.zip
wget https://cloud.uni-hamburg.de/s/5meqDbTbgydo6Tj/download/drugbank.zip -O drugbank.zip
wget https://cloud.uni-hamburg.de/s/PxWXAMY5bfS3ZcA/download/repotrial.zip -O repotrial.zip

for file in *.zip; do
    echo "Unzipping $file..."
    unzip -o "$file"
    rm -rf "$file"
done
cd ../../
mkdir -p nedrex_api/static
cd nedrex_api/static
wget https://cloud.uni-hamburg.de/s/PdXPnX77QpWzX7z/download -O static.zip
unzip -o static.zip
mv static/* .
rm -rf static
rm -rf static.zip
