.PHONY: help build-image run-container

CONTAINER_DIR      ?= .devcontainer
WORK_DIR           ?= $(shell pwd)/..
USERNAME     = $(shell whoami)
USER_UID     = $(shell id -u)
USER_GID     = $(shell id -g)
WORK_DIR     = $(shell pwd)/



SHARED_DIRS  = /home/$(USERNAME)/.config    \
            /home/$(USERNAME)/.ssh          \
            $(WORK_DIR)

IMAGE_NAME         ?= mdstream-client
CONTAINER_NAME     ?= $(IMAGE_NAME)-$(USERNAME)-$(shell date +"%Y-%m-%d.%H-%M")
DOCKER_FILE        ?= $(CONTAINER_DIR)/Dockerfile
DOCKER_ENTRYPOINT  ?= $(CONTAINER_DIR)/docker-entrypoint.sh

DOCKER_HTTP_PROXY  ?= $(HTTP_PROXY)
DOCKER_HTTPS_PROXY ?= $(HTTPS_PROXY)
DOCKER_NO_PROXY    ?= $(NO_PROXY)

HELP_MSG          += \trun-container            Run\
	a container from the ${IMAGE_NAME} image\n
HELP_MSG          += \tbuild-image              Build\
	the docker images ${IMAGE_NAME} with the required dependencies\n

directories:
	$(foreach dir, $(SHARED_DIRS), mkdir -p $(dir);)
	@touch $@


build-image: $(DOCKER_FILE) $(DOCKER_SCRIPTS)
	@docker build -t $(IMAGE_NAME)                                      \
        --build-arg ARG_HTTP_PROXY=$(DOCKER_HTTP_PROXY)               \
        --build-arg ARG_HTTPS_PROXY=$(DOCKER_HTTPS_PROXY)             \
        --build-arg ARG_NO_PROXY=$(DOCKER_NO_PROXY)                   \
        --build-arg ARG_DOCKER_ENTRYPOINT=$(DOCKER_ENTRYPOINT)        \
        --file $(DOCKER_FILE) .
	@touch $@

run-container: build-image directories
	@docker run -it --rm                                     \
	--name $(CONTAINER_NAME)                                 \
        --env USERNAME=$(USERNAME)                         \
        --env USER_UID=$(USER_UID)                         \
        --env USER_GID=$(USER_GID)                         \
        --env PYTHON_REQ=$(PYTHON_REQ)                     \
        --env HTTP_PROXY=$(DOCKER_HTTP_PROXY)              \
        --env HTTPS_PROXY=$(DOCKER_HTTPS_PROXY)            \
        --env WORK_DIR=$(WORK_DIR)                         \
        $(foreach dir, $(SHARED_DIRS), -v $(dir):$(dir))   \
    $(IMAGE_NAME)

clean-image:
	@docker rmi --force $(IMAGE_NAME)
	@rm -rf build-image
	@rm -rf directories
