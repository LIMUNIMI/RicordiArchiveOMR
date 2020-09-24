"""
Preprocess music score images and  creates blobs ready for annotations

Usage:
    preprocess.py (<in_pattern>) (<to_path>) [remove_staff]

"""
import glob
import os
from docopt import docopt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
from skimage import io, feature, exposure, util, transform
import numpy as np
from joblib import Parallel, delayed

extensions = ['.jpg', '.jpeg', '.png']
lbp_radius = 3
lbp_n_points = 8 * lbp_radius


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


def process(image, filename, to_path, remove_staff):
    if remove_staff:
        file = staff_removal(io.imsave('tmp.jpg', image))
        image = io.imread('tmp.jpg')

    if image.ndim > 2:
        raise RuntimeError(
            "Please, provide grayscale images or activate the `staff_remove` command"
        )

    blobs = find_blobs(image)

    data = []
    for blob in blobs:
        # circular Hough peaks
        radii = [3, 6, 12, 24, 48]
        hspaces = transform.hough_circle(blob, radii)
        peaks, _, _, _ = transform.hough_circle_peaks(hspaces,
                                                      radii,
                                                      threshold=0,
                                                      num_peaks=2)
        cpeaks = np.zeros(10)
        cpeaks[:peaks.shape[0]] = peaks
        # line Hough peaks
        hspaces, angles, dist = transform.hough_line(blob)
        peaks, _, _ = transform.hough_line_peaks(hspaces,
                                                 angles,
                                                 dist,
                                                 threshold=0,
                                                 num_peaks=10)
        lpeaks = np.zeros(10)
        lpeaks[:peaks.shape[0]] = peaks
        # lbp histogram
        lbp_hist, _ = exposure.histogram(feature.local_binary_pattern(
            blob, lbp_n_points, lbp_radius, method='var'),
            nbins=10,
            source_range='dtype')
        # histogram
        hist, _ = exposure.histogram(util.img_as_float(blob),
                                     nbins=10,
                                     source_range='dtype')
        # data.append(np.concatenate([lbp_hist, hist, [blob.size]]))
        data.append(
            np.concatenate([lbp_hist, hist, lpeaks, cpeaks, [blob.size]]))
    data = StandardScaler().fit_transform(data)
    data = PCA(n_components=10).fit_transform(data)
    clusters = AgglomerativeClustering(distance_threshold=10,
                                       n_clusters=None).fit_predict(data)

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
            os.path.join(to_root,
                         f"{base}_cl{clusters[i]:02d}_blob{i:03d}.png"), blob)

    # optionally clusterize blobs according to some feature
    # store blobs in new directory `to_path` with cluster directory


def new_glob(x): return glob.iglob(x, recursive=True)


def main(in_pattern, to_path, remove_staff):
    if not os.path.exists(to_path):
        os.mkdir(to_path)

    io.collection.glob = new_glob

    image_collection = io.ImageCollection(in_pattern)
    Parallel(n_jobs=-1)(delayed(process)(image, image_collection.files[i],
                                         to_path, remove_staff)
                        for i, image in enumerate(image_collection))


if __name__ == "__main__":

    args = docopt(__doc__)
    main(args['<in_pattern>'], args['<to_path>'], args['remove_staff'])
