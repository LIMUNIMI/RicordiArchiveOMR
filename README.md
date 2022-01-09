# OMR

## Setup

0. clone all submodules (`git clone --recursive`)
1. install pyenv: `curl https://pyenv.run | bash`

### Prepare staff-line-removal
2. install miniconda2 `PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install miniconda2-4.7.12`
3. `PYENV_VERSION=miniconda2-4.7.12 conda env create -f staffline.yml`
4. `PYENV_VERSION=miniconda2-4.7.12 conda init $(basename $SHELL)` (you may need to fix the command substitution syntax)
5. `exec $SHELL`

### Prepare our project
6. install python >= 3.9: `pyenv install 3.9.7`
7. install pdm: `curl -sSL https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py | python3 -`, other info on the [website](https://pdm.fming.dev/)
8. install dependencies: `pdm sync`

## Preprocess

1. setup the relative section in `config.toml`
2. remove staff-lines: `./preprocess.sh`; if it stops, you can restart it
3. `pdm run preprocess`

After this, you will find two files ending with `_nostaff.jpg` and
`_nostaff.json` for each file in the archive, containing the image without
staff and the data about that image (original file name, list of blobs, etc.).
You will also find a directory ending with `_nostaff` for each file in the
archive, containing the list of blobs, each in `png` format and accompanied by
a `.json` file containing the position, the parent image path and the
annotations (after the _Data Entry_ step).

## Data Entry

  `pdm run data_entry` 

This will start the Flask app listening on _all_ hosts requests to your machine
on port 1992. You can configure the port in `config.toml`, as well as other
options (documented in `config.toml`).

The server will create a 2 files:

* `__annotator.json`: 
  * keys are annotators (see `config.toml`);
  * value of each key is a list of lists where the i-th list represents the
  annotations given for the i-th control blob
* `__control.json`:
  * keys are `normal` and `control`
  * values are lists of string with the path of the blobs in each split
