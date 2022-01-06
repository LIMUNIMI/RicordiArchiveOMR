# OMR

## setup

0. clone all submodules (`git clone --recursive`)
1. Install pyenv: `curl https://pyenv.run | bash`
2. `PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 2.7.18`
3. `PYENV_VERSION=2.7.18 pip install -r staffline_requirements.txt`
4. clone [libgpuarray](https://github.com/Theano/libgpuarray/blob/master/doc/installation.rst), compile, and install from source with `PYENV_VERSION=2.7.18` flag on!
5. install python 3.9.6: `pyenv install 3.9.6`
5. Install pdm: `curl -sSL https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py | python3 -`
  other info on the [website](https://pdm.fming.dev/)
6. `pdm sync`

## preprocess
1. setup the relative section in `config.toml`
2. `pdm run preprocess`
