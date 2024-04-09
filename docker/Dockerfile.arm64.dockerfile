FROM szymanski2adesso/cadquery-client:2.4.0

RUN adduser --disabled-password --gecos "Default user" --uid 1000 cq

COPY run.sh /tmp/run.sh

VOLUME /home/cq/
WORKDIR /home/cq
EXPOSE 8888

USER cq 

ADD --chown=cq:cq run.sh /tmp
RUN chmod +x /tmp/run.sh

ENTRYPOINT ["/tmp/run.sh"]
