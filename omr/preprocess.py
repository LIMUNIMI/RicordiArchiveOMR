"""
Preprocess music score images and  creates blobs ready for annotations

Usage:
    preprocess.py (<in_pattern>) (<to_path>) [remove_staff]

"""
from docopt import docopt
from skimage import io, feature, exposure, util
from joblib import Parallel, delayed
import os

extensions = ['.jpg', '.jpeg', '.png']

def staff_removal(file):
    # TODO : add command for preprocessing
    pass


def find_blobs(image, method=feature.blob_dog):
    """
    Arguments
    ---------
    `image` : np.ndarray
    `method` : callable

    Returns
    -------
    list of np.ndarray :
        a list of images, each containing one blob
    """
    out = []
    blobs = method(image, min_sigma=10, max_sigma=50, threshold=0.1)
    for x, y, r in blobs:
        x, y, r = int(x), int(y), round(r)
        blob = image[max(0, x - r):min(image.shape[0], x + r),
                     max(0, y - r):min(image.shape[1], y + r)]
        out.append(blob)

    return out


def main(in_pattern, to_path, remove_staff):
    if not os.path.exists(to_path):
        os.mkdir(to_path)

    image_collection = io.ImageCollection(in_pattern)
    Parallel(n_jobs=-1)(
        delayed(process)(
            image, image_collection.files[i], to_path, remove_staff)
        for i, image in enumerate(image_collection)
    )


def process(image, filename, to_path, remove_staff):
    if remove_staff:
        file = staff_removal(io.imsave('tmp.jpg', image))
        image = io.imread('tmp.jpg')

    if image.ndim > 2:
        raise RuntimeError(
            "Please, provide grayscale images or activate the `staff_remove` command")

    blobs = find_blobs(image)
    root, file = os.path.split(filename)
    base, ext = os.path.splitext(file)
    to_root = os.path.join(to_path, root)

    if not os.path.exists(to_root):
        os.mkdir(to_root)

    for i, blob in enumerate(blobs):
        blob = exposure.rescale_intensity(blob, out_range='float')
        blob = util.img_as_uint(blob)
        # blob = exposure.equalize_hist(blob)
        io.imsave(
            os.path.join(to_root, base + f"_blob{i:03d}.png"), blob)

    # optionally clusterize blobs according to some feature
    # store blobs in new directory `to_path` with cluster directory


if __name__ == "__main__":

    args = docopt(__doc__)
    main(args['<in_pattern>'], args['<to_path>'], args['remove_staff'])
