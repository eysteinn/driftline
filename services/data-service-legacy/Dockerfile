FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o data-service ./cmd/data-service

FROM alpine:latest

WORKDIR /root/

COPY --from=builder /app/data-service .

EXPOSE 8000

CMD ["./data-service"]
