#!/bin/bash
echo "Starting service..."
. /opt/conda/bin/activate cq &&  \
cd /home/cq/app/ && \
fastapi run app/main.py --root-path=${URL_ROOT_PATH}