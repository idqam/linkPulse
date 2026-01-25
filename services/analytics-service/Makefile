.PHONY: build run test clean

build:
	go build -o bin/analytics-service ./cmd/server

run:
	go run ./cmd/server

test:
	go test -v ./...

test-coverage:
	go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

lint:
	golangci-lint run

clean:
	rm -rf bin/
	rm -f coverage.out coverage.html

docker-build:
	docker build -t analytics-service .

docker-run:
	docker run -p 8081:8081 --env-file .env analytics-service

tidy:
	go mod tidy
