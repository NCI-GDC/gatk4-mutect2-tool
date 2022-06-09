FROM quay.io/ncigdc/gatk:4.2.4.1 AS gatk
FROM quay.io/ncigdc/python38-builder AS builder

COPY ./ /opt

WORKDIR /opt

RUN pip install tox && tox -p

FROM quay.io/ncigdc/bio-openjdk:8u282-slim

COPY --from=builder / /
COPY --from=gatk /usr/local/bin/ /usr/local/bin/
COPY requirements.txt /opt/dist

WORKDIR /opt/dist

RUN apt update -y \
	&& apt install -y \
		libbz2-dev \
		liblzma-dev \
		zlib

RUN pip install -r requirements.txt \
	&& pip install *.tar.gz \
	&& rm -f *.tar.gz requirements.txt

WORKDIR /opt

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]
