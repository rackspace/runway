# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.241.1/containers/ubuntu/.devcontainer/base.Dockerfile

# [Choice] Ubuntu version (use ubuntu-22.04 or ubuntu-20.04 on local arm64/Apple Silicon): ubuntu-22.04, ubuntu-20.04
ARG VARIANT="ubuntu-22.04"
FROM mcr.microsoft.com/vscode/devcontainers/base:0-${VARIANT}

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends curl git make pkg-config bash-completion \
    python3-virtualenv python3-pip python3-venv python3-dev \
    software-properties-common binutils

# Setup Apt for newer versions of NodeJS
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash - &&\
    sudo apt-get install -y nodejs

# Install nodejs
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends nodejs

# Add additional python options
RUN sudo add-apt-repository ppa:deadsnakes/ppa

# Install Python 3.10, 3.8, and 3.9
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends python3.11 python3.11-venv python3.11-dev \
    python3.10 python3.10-venv python3.10-dev \
    python3.9 python3.9-venv python3.9-dev


# Setup alternatives
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1

# Update to use python 3.9 by default
RUN update-alternatives --set python $(update-alternatives --list python | grep python3.9)

# VSCODE user commands
USER vscode

# Setup Bash Completion
ADD --chown=vscode:vscode files/.bash_completion /home/vscode/.bash_completion
RUN mkdir /home/vscode/.bash_completion.d/

# Setup AWS CLI
RUN pip3 install --user awscli poetry==1.5.1
RUN echo "complete -C '/home/vscode/.local/bin/aws_completer' aws" >> ~/.bashrc

# Setup OS_NAME var for runway builds from this dev container
RUN echo "export OS_NAME=ubuntu-latest" >> ~/.bashrc
