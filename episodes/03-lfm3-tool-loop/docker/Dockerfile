FROM nvcr.io/nvidia/base/ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates curl python3 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 -s /bin/bash runner || usermod -l runner $(getent passwd 1000 | cut -d: -f1)
