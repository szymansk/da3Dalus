FROM szymanski2adesso/cadquery-client:2.4.0

SHELL [ "/bin/bash", "-c" ]

WORKDIR /home/cadquery
RUN source ${CONDA_INSTALL_DIR}/bin/activate \
    && conda activate --no-stack cadquery \
    && conda install -y -c conda-forge shapely jsonpickle

