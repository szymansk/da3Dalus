FROM ubuntu:22.04 AS build_avl

RUN mkdir -p /build
WORKDIR /build
COPY . /build

#COPY /build/Avl /home/avl/

SHELL [ "/bin/bash", "-c" ]
WORKDIR /build/Avl
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

RUN cd /build/Avl/plotlib \
    && make gfortran \
    && ln -s libPlt_gSP.a libPlt.a \
    && cd ..

RUN cd /build/Avl/eispack \
    && make -f Makefile.mingw \
    && ln -s eispack_gSP.a libeispack.a \
    && cd ..

RUN cd /build/Avl/bin \
    && make -f Makefile.gfortran avl



FROM condaforge/mambaforge:24.7.1-2

COPY --from=build_avl /build/Avl/bin/avl /usr/local/bin/

SHELL [ "/bin/bash", "-c" ]

RUN adduser --disabled-password --gecos "Default user" --uid 1000 cq && \
    apt-get update -y && \
    apt-get install --no-install-recommends -y libgl1-mesa-glx libglu1-mesa && \
    apt-get clean

RUN mamba create -n cq -y python=3.11 &&\
    mamba install -n cq -y -c conda-forge -c cadquery\
    OCP=7.7.2\
    #vtk=9.3.1\
    matplotlib=3.8\
    cadquery=2.4.0\
    shapely\
    jsonpickle\
    fastapi\
    pydantic\
    pip=24.0\
    casadi\#=3.7.0 \
    python-kaleido \
    &&\
    mamba clean --all &&\
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN source /opt/conda/bin/activate \
    && conda activate --no-stack cq \
    && pip install aerosandbox[full] \
    && pip install jupyter-cadquery==3.5.2 \
    && find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

#RUN . "/opt/conda/etc/profile.d/conda.sh" && conda activate cq && \
#    pip install jupyter-cadquery==3.5.2 && \
#    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN apt-get update \
    && apt-get install liblapack-dev -y \
    && apt-get install libblas-dev -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER cq
WORKDIR /home/cq/app
COPY --chown=cq:cq . .

#RUN cp /home/cq/app/docker/launch.sh .
#RUN chmod +x /home/cq/app/launch.sh

RUN mkdir -p tmp/exports

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-e","/home/cq/app/docker/launch.sh"]
