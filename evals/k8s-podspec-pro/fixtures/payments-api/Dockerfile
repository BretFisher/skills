# syntax=docker/dockerfile:1
FROM golang:1.25 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/payments-api ./cmd/api

FROM gcr.io/distroless/static-debian12 AS runtime
COPY --from=build /out/payments-api /payments-api
USER 65532:65532
EXPOSE 9090
ENTRYPOINT ["/payments-api"]
