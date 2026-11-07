# syntax=docker/dockerfile:1
FROM golang:1.25 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/watcher ./cmd/watcher

FROM gcr.io/distroless/static-debian12:nonroot AS runtime
COPY --from=build /out/watcher /watcher
USER 65532:65532
ENTRYPOINT ["/watcher"]
