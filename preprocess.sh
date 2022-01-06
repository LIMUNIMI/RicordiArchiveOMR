#!/bin/bash

# this script is here for demonstration purpose
# just activate the `staff_line_removal` conda nevironment and call this script
# with an image path as argument to test the staff-line-removal method
OLDIFS="$IFS"
IFS=$'\n' # bash specific
export THEANO_FLAGS="device=cuda0,force_device=True,floatX=float32"
export KERAS_BACKEND=theano
export LD_LIBRARY_PATH="/usr/local/lib/:$LD_LIBRARY_PATH"
echo "Processing file $1"

cd staff-lines-removal
# for i in $(find $1 -path $1/altro -prune -o -name "*.jpg")
# do
#     echo "Processing $i"
python demo.py -imgpath "$1" -modelpath MODELS/model_weights_GR_256x256_s256_l3_f96_k5_se1_e200_b8_p25_esg.h5 -layers 3 -window 256 -filters 96 -ksize 5 -th 0.3 -save ../demo_output_nostaff.jpg
# done
cd ..
IFS="$OLDIFS"
