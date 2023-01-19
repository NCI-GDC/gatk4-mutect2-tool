ARG REGISTRY=docker.osdc.io
ARG BASE_CONTAINER_VERSION=1.4.0
FROM ${REGISTRY}/ncigdc/gatk:4.2.4.1-26c1d2c AS gatk
# Using older Python image for compatibility
FROM ${REGISTRY}/ncigdc/python38-builder:1.4.0 AS builder

COPY ./ /opt

WORKDIR /opt

RUN pip install tox && tox -p

FROM ${REGISTRY}/ncigdc/python38-builder-jdk11

WORKDIR /opt

COPY --from=gatk /usr/local/bin/ /usr/local/bin/

COPY requirements.txt /opt/

RUN apt update -y \
	&& apt install -y \
		libbz2-dev \
		liblzma-dev \
		zlib1g

RUN ls / && ls /opt && pip install --no-deps -r requirements.txt \
	&& pip install --no-deps *.whl \
	&& rm -f *.whl requirements.txt

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]
