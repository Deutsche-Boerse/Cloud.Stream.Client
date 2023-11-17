FROM ubuntu:latest

ARG ARG_HTTP_PROXY
ARG ARG_HTTPS_PROXY
ARG ARG_NO_PROXY
ARG ARG_DOCKER_ENTRYPOINT
ARG BRANCH

ENV HTTP_PROXY  ${ARG_HTTP_PROXY}
ENV HTTPS_PROXY ${ARG_HTTPS_PROXY}
ENV NO_PROXY    ${ARG_NO_PROXY}
ENV http_proxy  ${ARG_HTTP_PROXY}
ENV https_proxy ${ARG_HTTPS_PROXY}
ENV no_proxy    ${ARG_NO_PROXY}
ENV BRANCH      ${BRANCH:-main}

RUN touch /etc/apt/apt.conf.d/proxy.conf                    && \
    echo "Acquire::http::Proxy \"${ARG_HTTP_PROXY}\";"          \
        >> /etc/apt/apt.conf.d/proxy.conf                   && \
    echo "Acquire::https::Proxy \"${ARG_HTTPS_PROXY}\";"        \
        >> /etc/apt/apt.conf.d/proxy.conf

# Update the package manager and install essential tools
RUN apt-get update                                  && \
    apt-get install -y build-essential              && \
    apt-get install -y wget                         && \
    apt-get install -y curl                         && \
    apt-get install -y g++                          && \
    apt-get install -y libssl-dev                   && \
    apt-get install -y libz-dev                     && \
    apt-get install -y make                         && \
    apt-get install -y python3                      && \
    apt-get install -y git                          && \
    apt-get install -y cmake                        && \
    apt-get install -y sudo                         && \
    apt-get install -y vim                          && \
    apt-get install -y python3                      && \
    apt-get install -y python3-pip 

# Install Cmake tool and add it to path
ARG CMAKE_BIN_PATH=/tmp/cmake/cmake-3.14.0-Linux-x86_64/bin
ENV PATH="${CMAKE_BIN_PATH}:${PATH}"
ENV BUILD_PREFIX "/usr"
WORKDIR /home/root

# Download and install protobuf3
RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v21.1/protobuf-all-21.1.tar.gz   && \
    tar -xf protobuf-all-21.1.tar.gz                                                                        && \
    cd protobuf-3.21.1                                                                                      && \
    mkdir -p build-shared && cd build-shared                                                                && \
    cmake -Dprotobuf_BUILD_SHARED_LIBS=on ../cmake                                                          && \
    make -j 16 install && make clean || exit 1

# Install IXWebSocket for mdstream-client-cpp
RUN curl -LO https://github.com/machinezone/IXWebSocket/archive/refs/tags/v11.4.3.tar.gz    && \
    tar -xf v11.4.3.tar.gz                                                                  && \
    cd IXWebSocket-11.4.3                                                                   && \
    mkdir -p build && cd build                                                              && \
    cmake ..                                                                                   \
        -DUSE_TLS=ON                                                                           \
        -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -g"                                            \
        -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG -g"                                              \
        -DCMAKE_INSTALL_PREFIX=${BUILD_PREFIX}                                                 \
        -DCMAKE_BUILD_TYPE=Release                                                          && \
    make -j 8 install && make clean

RUN git clone --depth 1 https://github.com/nlohmann/json.git       && \
    cp -r json/include/nlohmann /usr/include/                      && \
    rm -rf json

RUN pip install protobuf        && \
    pip install requests        && \
    pip install aiohttp         && \
    pip install jwt

RUN git clone https://github.com/Deutsche-Boerse/Cloud.Stream.Client.git && \
    cd Cloud.Stream.Client && \
    git checkout ${BRANCH} && \
    pip install --no-cache-dir -r python/requirements.txt && \
    make clean && \
    make proto-python

COPY ${ARG_DOCKER_ENTRYPOINT} /home/root/
RUN chmod +x /home/root/docker-entrypoint.sh

ENTRYPOINT ["/home/root/docker-entrypoint.sh"]
