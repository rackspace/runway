# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.241.1/containers/ubuntu/.devcontainer/base.Dockerfile

# [Choice] Ubuntu version (use ubuntu-22.04 or ubuntu-18.04 on local arm64/Apple Silicon): ubuntu-22.04, ubuntu-20.04, ubuntu-18.04
ARG VARIANT="ubuntu-22.04"
FROM mcr.microsoft.com/vscode/devcontainers/base:0-${VARIANT}

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends curl git make pkg-config bash-completion \
    python3-virtualenv python3-pip python3-venv python3-dev \
    software-properties-common npm binutils

# Symlink /usr/bin/python to /usr/bin/python3
RUN sudo ln -s /usr/bin/python3 /usr/bin/python

# VSCODE user commands
USER vscode

# Setup Bash Completion
ADD --chown=vscode:vscode files/.bash_completion /home/vscode/.bash_completion
RUN mkdir /home/vscode/.bash_completion.d/

# Setup AWS CLI
RUN pip3 install --user awscli
RUN echo "complete -C '/home/vscode/.local/bin/aws_completer' aws" >> ~/.bashrc

# Setup Poetry
RUN bash -c "curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python - \
    && echo 'export PATH=$HOME/.local/bin:\$PATH' >> ~/.bashrc"
RUN bash -c "export PATH=$HOME/.local/bin:\$PATH \
    && poetry completions bash > ~/.bash_completion.d/poetry.bash-completion"

# Setup OS_NAME var for runway builds from this dev container
RUN echo "export OS_NAME=ubuntu-22.04" >> ~/.bashrc
