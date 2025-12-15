ARG DOCKER_REGISTRY=ghcr.io
ARG VERSION=0.7.4
FROM $DOCKER_REGISTRY/kagent-dev/kagent/kagent-adk:$VERSION

WORKDIR /app

COPY . . 

RUN uv sync --locked --refresh

CMD ["agenteleilao"]