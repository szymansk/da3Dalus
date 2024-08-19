FROM szymanski2adesso/cadquery-client:2.4.0

SHELL [ "/bin/bash", "-c" ]

WORKDIR /home/cadquery
RUN source ${CONDA_INSTALL_DIR}/bin/activate \
    && conda activate --no-stack cadquery \
    && conda install -y -c conda-forge shapely jsonpickle

RUN adduser --disabled-password --gecos "Default user" --uid 1000 cq

COPY run.sh /tmp/run.sh

VOLUME /home/cq/
WORKDIR /home/cq
EXPOSE 8888

USER cq 

ADD --chown=cq:cq run.sh /tmp
RUN chmod +x /tmp/run.sh

ENTRYPOINT ["/tmp/run.sh"]
