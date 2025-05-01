FROM ubuntu:22.04 AS build_avl

RUN pwd && ls -al

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



FROM condaforge/mambaforge:24.7.1-2

COPY --from=build_avl /home/avl/bin/avl /usr/local/bin/

RUN adduser --disabled-password --gecos "Default user" --uid 1000 cq && \
    apt-get update -y && \
    apt-get install --no-install-recommends -y libgl1-mesa-glx libglu1-mesa && \
    apt-get clean

RUN mamba create -n cq -y python=3.10 &&\
    mamba install -n cq -y -c conda-forge -c cadquery\
    OCP=7.7.2\
    vtk=9.2\
    matplotlib=3.8\
    cadquery=master\
    shapely\
    jsonpickle\
    fastapi\
    pydantic\
    pip=24.0\
    casadi=3.7.0 \
    python-kaleido \
    && pip install aerosandbox[full] \
    &&\
    mamba clean --all &&\
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN . "/opt/conda/etc/profile.d/conda.sh" && conda activate cq && \
    pip install jupyter-cadquery==3.5.2 && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

USER cq
WORKDIR /home/cq/app
COPY --chown=cq:cq . .

#RUN cp /home/cq/app/docker/launch.sh .
#RUN chmod +x /home/cq/app/launch.sh

RUN mkdir -p tmp/exports

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-e","/home/cq/app/docker/launch.sh"]
