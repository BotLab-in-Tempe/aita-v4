# Dockerfile
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash coreutils findutils grep sed less && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
