IMAGE ?= registry.example.com/billing/invoicer
TAG   ?= $(shell git rev-parse --short HEAD)

.PHONY: image push

image:
	docker build -t $(IMAGE):$(TAG) .

push: image
	docker push $(IMAGE):$(TAG)
