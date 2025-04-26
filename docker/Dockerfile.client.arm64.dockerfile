FROM arm64v8/ubuntu:22.04 AS build_avl

COPY ./Avl /home/avl/

SHELL [ "/bin/bash", "-c" ]
WORKDIR /home/avl
RUN apt-get update \
    && apt-get install wget -y \
    && apt-get install build-essential -y \
    && apt-get install cmake -y \
    && apt-get install liblapack-dev -y \
    && apt-get install libblas-dev -y \
    && apt-get install libx11-dev -y \
    && apt-get install gfortran -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN cd plotlib \
    && make gfortran \
    && ln -s libPlt_gSP.a libPlt.a \
    && cd ..

RUN cd eispack \
    && make -f Makefile.mingw \
    && ln -s eispack_gSP.a libeispack.a \
    && cd ..

RUN cd bin \
    && make -f Makefile.gfortran avl


FROM szymanski2adesso/cadquery-client:2.4.0 AS cadquery_client

SHELL [ "/bin/bash", "-c" ]

# Copy AVL executable from build_avl stage to /usr/local/bin
COPY --from=build_avl /home/avl/bin/avl /usr/local/bin/

WORKDIR /home/cadquery

RUN apt-get update \
    && apt-get install liblapack-dev -y \
    && apt-get install libblas-dev -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN source ${CONDA_INSTALL_DIR}/bin/activate \
    && conda activate --no-stack cadquery \
    && conda install -y -c conda-forge  \
    shapely  \
    jsonpickle \
    fastapi \
    pydantic \
    casadi=3.7.0 \
    python-kaleido \
    && pip install aerosandbox[full]
