FROM ubuntu:bionic
MAINTAINER Onica Group LLC <https://github.com/onicagroup>

# dependencies
RUN apt-get update && apt-get install -y \
        curl \
        python-pip \
        python-minimal \
        unzip \
        git \
        uuid-runtime \
        nano && \
    curl -sL https://deb.nodesource.com/setup_8.x | bash - && \
    apt-get install -y nodejs

# terraform
RUN curl -o tf.zip https://releases.hashicorp.com/terraform/0.11.7/terraform_0.11.7_linux_amd64.zip && \
    unzip tf.zip && \
    mv terraform /usr/local/bin/

# runway
RUN echo 'export PATH=$HOME/.local/bin:$PATH' >> ${HOME}/.bashrc && \
    /bin/bash -c "source ${HOME}/.bashrc" && \
    pip install --user runway

# confirm
RUN echo $(python --version) \
    "Node "$(node --version) \
    "\n"$(terraform --version) \
    "\nRunway v"$(/root/.local/bin/runway --version)
    # should return output similar to:
        # Python 2.7.12
        # Node v8.11.3
        # Terraform v0.11.7
        # Runway v0.20.3
