FROM golang:1.25-alpine AS builder

RUN apk add --no-cache git
WORKDIR /src

# Pin the official source so rebuilding does not silently change MinIO.
ARG MINIO_COMMIT=7aac2a2c5b7c882e68c1ce017d8256be2feea27f
RUN git init \
    && git remote add origin https://github.com/minio/minio.git \
    && git fetch --depth 1 origin "${MINIO_COMMIT}" \
    && git checkout --detach FETCH_HEAD

RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath \
    -ldflags="$(go run buildscripts/gen-ldflags.go)" \
    -o /out/minio .

FROM alpine:3.23
RUN apk add --no-cache ca-certificates curl
COPY --from=builder /out/minio /usr/local/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
