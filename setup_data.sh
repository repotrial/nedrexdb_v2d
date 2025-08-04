#!/usr/bin/env bash
NEDREX_FILES=$1
DOWNLOADS=$NEDREX_FILES/nedrex_data/downloads

mkdir -p $DOWNLOADS
cd $DOWNLOADS
echo "Starting dump downloads"
wget https://cloud.uni-hamburg.de/s/RiAtjZC3bb7bg7n/download/bioontology.zip -q -O bioontology.zip
echo "Downloaded bioontology.zip"
wget https://cloud.uni-hamburg.de/s/5meqDbTbgydo6Tj/download/drugbank.zip -q -O drugbank.zip
echo "Downloaded drugbank.zip"
wget https://cloud.uni-hamburg.de/public.php/dav/files/9wNb5HWL7RBH6ng/?accept=zip -q -O disgenet.zip
echo "Downloaded disgenet.zip"
wget https://cloud.uni-hamburg.de/s/PxWXAMY5bfS3ZcA/download/repotrial.zip -q -O repotrial.zip
echo "Downloaded repotrial.zip"

for file in *.zip; do
    echo "Unzipping $file..."
    unzip -o "$file"
    rm -rf "$file"
done
cd ../../
mkdir -p nedrex_api/static
cd nedrex_api/static
wget https://cloud.uni-hamburg.de/s/PdXPnX77QpWzX7z/download -q -O static.zip
echo "Downloaded static.zip"
unzip -o static.zip
mv static/* .
rm -rf static
rm -rf static.zip
