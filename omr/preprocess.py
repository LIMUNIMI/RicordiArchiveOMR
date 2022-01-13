"""
Preprocess music score images and  creates blobs ready for annotations

Usage:
    preprocess.py (<in_pattern>) (<to_path>)

"""
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
from tqdm import tqdm

lbp_radius = 3
lbp_n_points = 8 * lbp_radius


@dataclass
class Blob:
    image: np.ndarray
    x0: int
    y0: int
    x1: int
    y1: int


def remove_staffs(self,
                  fname: Optional[Path] = None,
                  image: Optional[np.ndarray] = None):
    """ Run the staff-removal algorithm. If `fname` is None, `image` is used
    and an array is returned, otherise, `fname` is used and a filename is returned.

    For some reason, it doesn't work
    """
    import os
    assert fname is not None or image is not None, "Please, provide a file or an array"

    if image is not None:
        _, fname = tempfile.mkstemp('.jpg')
        io.imsave(fname, image)

    outfname = str(fname.with_suffix('')) + '_nostaff.jpg'
    proj_dir = Path('__file__').parent.parent
    subprocess.run(
        ['bash', str(proj_dir / 'preprocess.sh'),
         str(fname), outfname])

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


def process(filename: Path,
            from_path: Path,
            to_path: Path,
            staff_removal=False,
            clustering=False):
    original_filename = filename
    if staff_removal:
        filename = remove_staffs(fname=filename)

    image = io.imread(filename)

    blobs = find_blobs(image)

    data = []
    if clustering:
        for blob_obj in blobs:
            blob = blob_obj.image
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
        data = PCA(n_components=min(10, min(
            data.shape[0], data.shape[1]))).fit_transform(data)
        clusters = AgglomerativeClustering(distance_threshold=10,
                                           n_clusters=None).fit_predict(data)

    to_root = to_path / filename.relative_to(from_path).with_suffix('')
    to_root.mkdir(parents=True, exist_ok=True)

    json_data = {
        "img_path": str(original_filename),
        "nostaff_path": str(filename),
        "blobs": []
    }
    for i, blob_obj in enumerate(blobs):
        blob = blob_obj.image
        blob = exposure.rescale_intensity(blob, out_range='float')
        blob = util.img_as_uint(blob)
        # blob = exposure.equalize_hist(blob)
        blob_path = to_root / f"{filename.stem}_blob{i:03d}.png"
        io.imsave(blob_path, blob)

        # storing into the json structure
        blob_obj.path = str(blob_path)
        blob_obj.parent = str(original_filename)
        blob_obj.id = i
        if clustering:
            blob_obj.cluster = clusters[i]
        del blob_obj.image
        blob_json_path = str(blob_path.with_suffix('.json'))
        json.dump(blob_obj.__dict__, open(blob_json_path, "w"))
        json_data["blobs"].append(blob_json_path)

    json.dump(json_data, open(original_filename.with_suffix('.json'), "w"))


def main(toml_config: str):
    import toml
    conf = toml.load(open(toml_config))
    to_path = Path(conf['preprocessing']['blob_dir'])
    in_path = Path(conf['preprocessing']['input_dir'])
    in_pattern = in_path.glob('**/*_nostaff.jpg')

    Parallel(n_jobs=10,
             backend='multiprocessing')(delayed(process)(
                 file, in_path, to_path, staff_removal=False, clustering=False)
                                        for file in tqdm(list(in_pattern)))


if __name__ == "__main__":

    import sys
    main(sys.argv[1], sys.argv[2])
