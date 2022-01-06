#!/bin/bash

OLDIFS="$IFS"
IFS=$'\n' # bash specific
export THEANO_FLAGS="device=cuda0,force_device=True,floatX=float32"
export KERAS_BACKEND=theano
export LD_LIBRARY_PATH="/usr/local/lib/:$LD_LIBRARY_PATH"

# reading config
data_path=$(grep input_dir config.toml | awk '{print $3}' | xargs)
# adding final slash if needed
data_path="${data_path%/}/"

cd staff-lines-removal

# for each jpg file in the dataset that is not in `altro` directory
for i in $(find $data_path -path ${data_path}/altro -prune -o -name "*.jpg")
do
  echo
  echo
  echo "====================================================="
  echo "Processing $i"
  echo "====================================================="
  echo
  echo
  PYENV_VERSION=miniconda2-4.7.12/envs/staff_line_removal python demo.py -imgpath "$i" -modelpath MODELS/model_weights_GR_256x256_s256_l3_f96_k5_se1_e200_b8_p25_esg.h5 -layers 3 -window 256 -filters 96 -ksize 5 -th 0.3 -save "${i/.jpg/_nostaff.jpg}"
done
cd ..
IFS="$OLDIFS"
