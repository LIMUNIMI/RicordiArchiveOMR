# OMR

## setup

0. clone all submodules
1. Install pyenv:
2. `PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 2.7.14`
3. `cd staff-lines-removal`
4. `pyenv local 2.7.14`
5. `pip install -r ../staffline_requirements.txt`
6. clone libpygpuarray and compile and install from source
7. `cd ..`
8. Install *poetry*: `curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python`
9. `poetry install`

## preprocess
1. `./preprocess.sh [dir to data without ending /]`
2. `poetry run python -m omr.preprocess 'dataset/**/*_nostaff.jpg' 'processed' 
