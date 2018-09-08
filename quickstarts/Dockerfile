FROM ubuntu:bionic
MAINTAINER Onica Group LLC <https://github.com/onicagroup>

RUN set -xe && \
  apt-get update && \
  apt-get -y install \
    curl \
    git \
    nano \
    npm \
    python-pip \
    unzip \
    uuid-runtime \
    vim && \
  rm -rf /var/lib/apt/lists/* && \
  update-alternatives --install /usr/bin/node node /usr/bin/nodejs 10 && \
  npm install npm@latest -g && \
  curl -o tf.zip https://releases.hashicorp.com/terraform/0.11.7/terraform_0.11.7_linux_amd64.zip && \
  unzip tf.zip && \
  mv terraform /usr/local/bin/ && \
  pip install ply && \
  pip install pipenv runway

CMD ["bash"]
