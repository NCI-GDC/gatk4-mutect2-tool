FROM quay.io/ncigdc/gatk:4.2.4.1 AS gatk
FROM quay.io/ncigdc/python38 AS python

ENV BINARY gatk4-mutect2-tool

COPY --from=python / /
COPY --from=gatk /usr/local/bin/ /usr/local/bin/

COPY ./dist/ /opt
WORKDIR /opt

RUN apt-get update \
	&& apt-get install make \
	&& rm -rf /var/lib/apt/lists/*

RUN make init-pip \
  && ln -s /opt/bin/${BINARY} /usr/local/bin/${BINARY}

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--", "gatk4_mutect2_tool"]
CMD ["--help"]
