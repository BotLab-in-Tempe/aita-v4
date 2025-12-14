# Dockerfile
# docker build -t aita-sandbox:latest .

FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash coreutils findutils grep sed less tzdata && \
    rm -rf /var/lib/apt/lists/*

ENV TZ=America/Denver
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /workspace
