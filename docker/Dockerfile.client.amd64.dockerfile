FROM condaforge/mambaforge:24.7.1-2

RUN adduser --disabled-password --gecos "Default user" --uid 1000 cq && \
    apt-get update -y && \
    apt-get install --no-install-recommends -y libgl1-mesa-glx libglu1-mesa && \
    apt-get clean

RUN mamba create -n cq -y python=3.10 && \
    mamba install -n cq -y -c conda-forge -c cadquery  \
    OCP=7.7.2  \
    vtk=9.2  \
    matplotlib=3.8  \
    cadquery=master \
    shapely  \
    jsonpickle  \
    fastapi \
    pydantic \
    pip=24.0 \
    && \
    mamba clean --all && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN . "/opt/conda/etc/profile.d/conda.sh" && conda activate cq && \
    pip install jupyter-cadquery==3.5.2 && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

USER cq
WORKDIR /home/cq/app
COPY --chown=cq:cq . .

ADD --chown=cq:cq ./docker/launch.sh /home/cq/app
RUN chmod +x ./launch.sh

RUN mkdir -p tmp/exports

EXPOSE 8000

ENTRYPOINT ["/home/cq/app/launch.sh"]
