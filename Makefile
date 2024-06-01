# Makefile
# hunterbounter.com 2024
# Project Name
IMAGE_NAME=hunter_bounter_zapv1

build:
	docker build -t $(IMAGE_NAME) .

build-nocache:
	docker build --no-cache -t $(IMAGE_NAME) .

run:
	docker run -u root  -p 5002:5002  --dns 1.1.1.1 -i $(IMAGE_NAME)

clean:
	docker rm -f $(IMAGE_NAME)
	docker rmi $(IMAGE_NAME)

rebuild: clean build run

.PHONY: build run clean rebuild
