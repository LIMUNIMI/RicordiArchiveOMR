# OMR

## setup

0. clone all submodules (`git clone --recursive`)
1. Install pyenv: `curl https://pyenv.run | bash`
2. `PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 2.7.18`
3. `PYENV_VERSION=2.7.18 pip install -r staffline_requirements.txt`
4. clone [libgpuarray](https://github.com/Theano/libgpuarray/blob/master/doc/installation.rst), compile, and install from source with `PYENV_VERSION=2.7.18` flag on!
5. install python 3.10.1: `pyenv install 3.10.1`
5. create venv `python -m venv venv`
6. `pip install joblib scikit-image scikit-learn`

## preprocess
`poetry run python -m omr.preprocess /path/to/dataset/**/*.jpg /path/to/output`
