ARG REGISTRY=docker.osdc.io
ARG BASE_CONTAINER_VERSION=2.1.0
FROM ${REGISTRY}/ncigdc/gatk:4.2.4.1-26c1d2c AS gatk
FROM ${REGISTRY}/ncigdc/python3.8-builder:${BASE_CONTAINER_VERSION}} AS builder

COPY ./ /opt

WORKDIR /opt

RUN pip install tox && tox -p

FROM ${REGISTRY}/ncigdc/bio-openjdk:8u282-slim

COPY --from=builder / /
COPY --from=gatk /usr/local/bin/ /usr/local/bin/
COPY requirements.txt /opt/dist

WORKDIR /opt/dist

RUN apt update -y \
	&& apt install -y \
		libbz2-dev \
		liblzma-dev \
		zlib1g

RUN pip install -r requirements.txt \
	&& pip install *.tar.gz \
	&& rm -f *.tar.gz requirements.txt

WORKDIR /opt

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]
