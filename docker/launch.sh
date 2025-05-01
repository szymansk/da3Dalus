#!/bin/bash
echo "Starting service..."
export DISPLAY_CONSTRUCTION_STEP=0
. /opt/conda/bin/activate cq &&  \
cd /home/cq/app/ && \
fastapi run app/main.py --root-path=${URL_ROOT_PATH}