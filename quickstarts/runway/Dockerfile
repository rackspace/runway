FROM ubuntu:24.04

ARG PYTHON_VERSION="3.12.5"

SHELL ["/bin/bash", "--login", "-o", "pipefail", "-c"]

RUN set -ex; \
  apt-get update; \
  apt-get install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl git \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev\
    npm; \
  rm -rf /var/lib/apt/lists/*;

ENV PYTHON_VERSION="${PYTHON_VERSION}"
ENV PYENV_ROOT="/usr/local/share/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

# Install python
RUN set -ex; \
  curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash; \
  PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install "${PYTHON_VERSION}"; \
  pyenv global "${PYTHON_VERSION}"; \
  "${PYENV_ROOT}/versions/${PYTHON_VERSION}/bin/pip" install --disable-pip-version-check --upgrade pip setuptools wheel; \
  "${PYENV_ROOT}/versions/${PYTHON_VERSION}/bin/pip" install pipx; \
  mkdir ~/.profile.d; \
  echo 'eval "$(pyenv init -)";' >> ~/.profile.d/001-pyenv.sh; \
  echo 'if [ -d ~/.profile.d ]; then for rc in ~/.profile.d/*.sh; do if [ -f "$rc" ]; then . "$rc"; fi done fi; unset rc;' > ~/.profile

# Install runway - it is recommend to install poetry instad and use poetry to install runway per-project
RUN set -ex; \
  pipx ensurepath; \
  pipx install runway

CMD ["bash"]
