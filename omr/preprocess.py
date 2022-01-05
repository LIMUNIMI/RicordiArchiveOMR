"""
Preprocess music score images and  creates blobs ready for annotations

Usage:
    preprocess.py (<in_pattern>) (<to_path>)

"""
import glob
import os
from pathlib import Path
import subprocess
from typing import Optional
import tempfile
from dataclasses import dataclass
import json

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
from skimage import io, feature, exposure, util, transform
import numpy as np
from joblib import Parallel, delayed

lbp_radius = 3
lbp_n_points = 8 * lbp_radius


@dataclass
class Blob:
    image: np.ndarray
    x0: int
    y0: int
    x1: int
    y1: int


class StaffRemover():

    def __init__(self):
        self.environ = os.environ.copy()
        self.environ[
            "THEANO_FLAGS"] = "device=cuda0,force_device=True,floatX=float32"
        self.environ["KERAS_BACKEND"] = "theano"
        self.environ["LD_LIBRARY_PATH"] = "/usr/local/lib/:$LD_LIBRARY_PATH"
        self.environ["PYENV_VERSION"] = "2.7.18"

    def get_cmd(self, infile, outfile):
        os.chdir('staff-lines-removal')
        return [
            'pyenv', 'exec', 'python', 'demo.py', '-imgpath', infile,
            '-modelpath MODELS/model_weights_GR_256x256_s256_l3_f96_k5_se1_e200_b8_p25_esg.h5',
            '-layers', '3', '-window', '256', '-filters', '96', '-ksize', '5',
            '-th', '0.3', '-save', outfile
        ]
        os.chdir('..')

    def run(self,
            fname: Optional[Path] = None,
            image: Optional[np.ndarray] = None):
        """
        Run the staff-removal algorithm. If `fname` is None, `image` is used
        and an array is returned, otherise, `fname` is used and a filename is returned.
        """
        assert fname is not None or image is not None, "Please, provide a file or an array"

        if image is not None:
            _, fname = tempfile.mkstemp('.jpg')
            io.imsave(fname, image)

        outfname = str(fname.with_suffix('')) + '_nostaff.jpg'
        subprocess.run(self.get_cmd(str(fname), outfname))

        if image is not None:
            out = io.imread(outfname)
            os.remove(outfname)
        else:
            out = outfname

        return out


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
        x0 = max(0, x - r)
        x1 = min(image.shape[0], x + r)
        y0 = max(0, y - r)
        y1 = min(image.shape[1], y + r)
        blob = image[x0:x1, y0:y1]
        out.append(Blob(blob, x0, y0, x1, y1))

    return out


def process(filename, to_path, staff_remover):
    original_filename = filename
    filename = staff_remover.run(fname=filename)

    image = io.imread(filename)

    blobs = find_blobs(image)

    data = []
    for blob_obj in blobs:
        blob = blob_obj.blob
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
    data = PCA(n_components=min(10, min(data.shape[0],
                                        data.shape[1]))).fit_transform(data)
    clusters = AgglomerativeClustering(distance_threshold=10,
                                       n_clusters=None).fit_predict(data)

    root, file = os.path.split(filename)
    base, ext = os.path.splitext(file)
    if root[0] == '/':
        root = root[1:]
    to_root = os.path.join(to_path, root)

    if not os.path.exists(to_root):
        Path(to_root).mkdir(parents=True, exist_ok=True)

    json_data = {
        "img_path": original_filename,
        "nostaff_path": filename,
        "blobs": []
    }
    for i, blob_obj in enumerate(blobs):
        blob = blob_obj.blob
        blob = exposure.rescale_intensity(blob, out_range='float')
        blob = util.img_as_uint(blob)
        # blob = exposure.equalize_hist(blob)
        blob_path = os.path.join(
            to_root, f"{base}_cl{clusters[i]:02d}_blob{i:03d}.png")
        io.imsave(blob_path, blob)

        # storing into the json structure
        blob_obj.path = blob_path
        blob_obj.id = i
        blob_obj.cluster = clusters[i]
        blob_obj.type = None
        json.dump(blob_obj.__dict__, open(blob_path.with_suffix('.json')))
        json_data["blobs"].append(blob_path)

    json.dump(json_data, open(original_filename.with_suffix('.json')))


def main(in_pattern, to_path):
    staff_remover = StaffRemover()

    if not os.path.exists(to_path):
        Path(to_path).mkdir(parents=True, exist_ok=True)

    Parallel(n_jobs=10)(delayed(process)(Path(file), to_path, staff_remover)
                        for file in glob.iglob(in_pattern, recursive=True))


if __name__ == "__main__":

    import sys
    main(sys.argv[1], sys.argv[2])
