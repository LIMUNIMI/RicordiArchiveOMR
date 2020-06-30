#!/bin/sh
OLDIFS="$IFS"
IFS=$'\n' # bash specific
export THEANO_FLAGS="device=cuda0,force_device=True,floatX=float32"
export KERAS_BACKEND=theano
export LD_LIBRARY_PATH="/usr/local/lib/:$LD_LIBRARY_PATH"
echo "Analyzing dir $1"

cd staff-lines-removal
for i in $(find $1 -path $1/altro -prune -o -name "*.jpg")
do
    echo "Processing $i"
    pyenv exec python demo.py -imgpath "$i" -modelpath MODELS/model_weights_GR_256x256_s256_l3_f96_k5_se1_e200_b8_p25_esg.h5 -layers 3 -window 256 -filters 96 -ksize 5 -th 0.3 -save "${i/.jpg/_nostaff.jpg}"
done
cd ..
IFS="$OLDIFS"
