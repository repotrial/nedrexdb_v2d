#!/usr/bin/bash

docker network create nedrexdb_default
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d