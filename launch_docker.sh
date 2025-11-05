#!/usr/bin/bash

# add c as a cmd option without argument.
while getopts c name
do
        case $name in
          c)no_cache=1;;
          *)echo "Invalid arg $name";;
        esac
done

docker network create nedrexdb_default

# decide whether to use cache or not
if [[ ! -z $no_cache ]]
then
  docker compose -f docker-compose.dev.yml build --no-cache
  docker compose -f docker-compose.dev.yml up -d --force-recreate
else
  docker compose -f docker-compose.dev.yml build
  docker compose -f docker-compose.dev.yml up -d
fi