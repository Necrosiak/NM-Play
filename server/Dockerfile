FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod ./
RUN go mod tidy
COPY . .
RUN go mod tidy && go build -o nm-play-server ./cmd/server

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/nm-play-server .
EXPOSE 11451/udp
EXPOSE 11452/udp
EXPOSE 27312/tcp
EXPOSE 8080/tcp
CMD ["./nm-play-server"]