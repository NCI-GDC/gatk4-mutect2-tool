FROM quay.io/ncigdc/gatk:4.2.4.1 AS gatk
FROM quay.io/ncigdc/python38-builder as builder

COPY ./ /opt

WORKDIR /opt

RUN pip install tox && tox -p

FROM quay.io/ncigdc/python38

COPY --from=builder /opt/dist/*.tar.gz /opt
COPY --from=gatk /usr/local/bin/ /usr/local/bin/
COPY requirements.txt /opt

WORKDIR /opt

RUN pip install -r requirements.txt \
	&& pip install *.tar.gz \
	&& rm -f *.tar.gz requirements.txt

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--", "gatk4_mutect2_tool"]

CMD ["--help"]
