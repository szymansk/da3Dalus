FROM condaforge/mambaforge:24.1.2-0

RUN adduser --disabled-password --gecos "Default user" --uid 1000 cq && \
    apt-get update -y && \
    apt-get install --no-install-recommends -y libgl1-mesa-glx libglu1-mesa && \
    apt-get clean

RUN mamba create -n cq -y python=3.10 && \
    mamba install -n cq -y -c conda-forge -c cadquery OCP=7.7.2 vtk=9.2 matplotlib=3.5  \
    shapely  \
    jsonpickle  \
    fastapi \
    pydantic \
    && \
    mamba clean --all && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN mamba install -n cq -y -c conda-forge -c cadquery cadquery=master && \
    mamba clean --all && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN . "/opt/conda/etc/profile.d/conda.sh" && conda activate cq && \
    pip install jupyter-cadquery==3.5.2 cadquery-massembly~=1.0.0 jupyterlab~=3.5 voila~=0.3.5 && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

COPY run_amd64.sh /tmp/run_amd64.sh

VOLUME /home/cq/
WORKDIR /home/cq
EXPOSE 8888

USER cq

ADD --chown=cq:cq run_amd64.sh /tmp
RUN chmod +x /tmp/run_amd64.sh

# ENTRYPOINT ["tail","-f","/dev/null"]

ENTRYPOINT ["/tmp/run_amd64.sh"]
