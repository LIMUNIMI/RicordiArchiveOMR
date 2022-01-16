import os
import json
from pathlib import Path
import uuid
import logging

import numpy as np
from scipy.stats import spearmanr
from skimage import io

RNG = np.random.default_rng(1992)

LOGGER = logging.getLogger(__name__)


def setup_logger(logger):
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    filehandler = logging.FileHandler("server.log")
    filehandler.setLevel(logging.INFO)
    filehandler.setFormatter(formatter)
    logger.addHandler(filehandler)

    iohandler = logging.StreamHandler()
    iohandler.setLevel(logging.INFO)
    iohandler.setFormatter(formatter)
    logger.addHandler(iohandler)


setup_logger(LOGGER)


def read_json_field(fname, annotation_field):
    data = json.load(open(fname, "r"))
    if annotation_field in data:
        return data[annotation_field]
    else:
        return None


def draw_rectangle(image, x0, y0, x1, y1, color=(255, 0, 0)):
    xmax = image.shape[0] - 1
    ymax = image.shape[1] - 1
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(xmax, x1)
    y1 = min(ymax, y1)
    image[x0:x1, y0, :] = color
    image[x0:x1, y1, :] = color
    image[x0, y0:y1, :] = color
    image[x1, y0:y1, :] = color
    return image


class EndedHistoryException(RuntimeError):
    pass


class ImageManager:
    """
    An iterator that provides the next image that must be annotated
    """

    def __init__(self,
                 blob_pattern,
                 annotation_field,
                 annotator,
                 control_length=100,
                 control_freq=200,
                 annotator_json_fn='__annotator.json',
                 control_json_fn='__control.json',
                 static_dir='./static',
                 enlarge=50):

        assert control_length or control_json_fn, "Please, provide control_length or control_json_fn and normal_json_fn"
        # shuffling blobs
        full_json_list = np.asarray([str(i) for i in blob_pattern])
        RNG.shuffle(full_json_list)  # in-place...

        # splitting control set
        if os.path.exists(control_json_fn):
            _data = json.load(open(control_json_fn))
            self.control_jsons = _data['control']
            self.normal_jsons = _data['normal']
        else:
            self.control_jsons = full_json_list[:control_length]
            self.normal_jsons = full_json_list[control_length:]
            json.dump(
                {
                    'control': self.control_jsons.tolist(),
                    'normal': self.normal_jsons.tolist()
                }, open(control_json_fn, "w"))

        # initializing fields
        self.current_normal_idx = 0
        self.current_control_idx = -1
        self.annotation_field = annotation_field
        self.control_freq = control_freq
        self.static_dir = Path(static_dir)
        self.static_dir.mkdir(exist_ok=True, parents=True)
        self.control_length = control_length
        self.history = []

        # initializing annotator_json
        self.annotator_json_fn = annotator_json_fn
        self.annotator = annotator
        self._annotator_rating = []
        self._new_annotator_rating = False
        if os.path.exists(annotator_json_fn):
            self.__init_annotator(annotator)
        else:
            annotator_json = {annotator: [[] for _ in range(control_length)]}
            json.dump(annotator_json, open(annotator_json_fn, "w"))

        self.is_control = False
        self.enlarge = enlarge

    def __init_annotator(self, annotator):
        annotator_json = json.load(open(self.annotator_json_fn))
        if annotator not in annotator_json:
            annotator_json[annotator] = [[]
                                         for _ in range(self.control_length)]
        json.dump(annotator_json, open(self.annotator_json_fn, "w"))
        self.update_rating(annotator_json, self.annotator)

    def __get_next_json(self):
        """
        Get the next json from normal or control group and adds its info to the history
        """
        # checking if we should provide a control json
        if RNG.random() < 1 / self.control_freq:
            is_control = True
            # pick next control blob
            # update `current_control_idx`
            self.current_control_idx += 1
            if self.current_control_idx >= len(self.control_jsons):
                self.current_control_idx = 0
            LOGGER.info(f"control_idx: {self.current_control_idx}")
            blob_json = self.control_jsons[self.current_control_idx]
        else:
            is_control = False
            # looking for the first json not annotated
            FOUND = False
            # here and there, recompute `current_normal_idx` to annotate jsons
            # that may have been skipped
            if RNG.random() < 0.001:
                self.current_normal_idx = 0
            for idx, json_fname in enumerate(
                    self.normal_jsons[self.current_normal_idx:]):
                if read_json_field(json_fname, self.annotation_field) is None:
                    FOUND = True
                    blob_json = json_fname
                    # update `current_normal_idx`
                    self.current_normal_idx += idx + 1
                    LOGGER.info(
                        f"Current_normal_idx: {self.current_normal_idx}/{len(self.normal_jsons)}"
                    )
                    break
            if not FOUND:
                raise StopIteration
        # add arguments to the history
        self.history.append((blob_json, is_control))
        return blob_json, is_control

    def __serve_image(self, blob_json, is_control):
        """
        does everything to serve an image

        Returns:
        * annotation_json : the json path that should be annotated
        * is_control : if this json is one from control group
        * the unique id used to generate the served images (use it in
          `get_filenames` to get the path that should be servedunique_id
        * the list of directories that compose the original image (use it to
          retrieve author name and opera)
        """

        # copy the image in a place visible to the server
        # if we want to show the original image, we should put it here
        b = json.load(open(blob_json))

        # original_image_path = Path(
        #     str(Path(b["path"]).parent).replace('_nostaff', '') + '.jpg')
        original_image_path = Path(b["parent"].replace('_nostaff', ''))

        # sectioning the blob
        original_image = io.imread(original_image_path)
        # section = original_image[b["x0"]:b["x1"], b["y0"]:b["y1"]]
        x_max = original_image.shape[0]
        y_max = original_image.shape[1]
        e = self.enlarge
        x0 = max(0, b["x0"] - e)
        x1 = min(x_max, b["x1"] + e)
        y0 = max(0, b["y0"] - e)
        y1 = min(y_max, b["y1"] + e)
        big_section = original_image[x0:x1, y0:y1]
        big_section = draw_rectangle(big_section.copy(), b["x0"] - x0,
                                     b["y0"] - y0, b["x1"] - x1 or x_max,
                                     b["y1"] - y1 or y_max)
        # drawing a rectangle in the original image
        partiture = draw_rectangle(original_image.copy(), b["x0"], b["y0"],
                                   b["x1"], b["y1"])

        unique_id = str(uuid.uuid4())
        big_blob_jpg, partiture_jpg = self.get_filenames(unique_id)

        # io.imsave(blob_jpg, section)
        io.imsave(big_blob_jpg, big_section)
        io.imsave(partiture_jpg, partiture)

        return blob_json, is_control, unique_id, list(
            original_image_path.parts)

    def __next__(self):
        """
        Returns `self.__serve_image(*self.__get_next_json())`
        """
        return self.__serve_image(*self.__get_next_json())

    def __back__(self, idx):
        """
        Looks in the history and serves the image at the `-idx` index in the history
        If idx > history length, raise EndedHistoryException
        """

        if idx > len(self.history):
            raise EndedHistoryException()

        return self.__serve_image(*self.history[-idx])

    def ask(self, idx):
        """
        A proxy method for `__next__` and `__back__`. If `idx` is `None`,
        `__next__` is called, otherwise it calls `__back__`
        """
        if idx is None:
            return self.__next__()
        else:
            return self.__back__(idx)

    def get_filenames(self, unique_id):
        big_blob_jpg = self.static_dir / (unique_id + "_big_blob.jpg")
        partiture_jpg = self.static_dir / (unique_id + "_partiture.jpg")
        return big_blob_jpg, partiture_jpg

    def cleaning(self, unique_id):
        for f in self.get_filenames(unique_id):
            f.unlink(missing_ok=True)

    def save_annotation(self, json_fn, is_control, annotation_value,
                        unique_id):
        if is_control:
            # this was a control blob
            annotator_json = json.load(open(self.annotator_json_fn))
            if self.annotator not in annotator_json:
                self.__init_annotator(self.annotator)
                annotator_json = json.load(open(self.annotator_json_fn))
            annotator_json[self.annotator][self.current_control_idx].append(
                annotation_value)
            self.update_rating(annotator_json, self.annotator)
            json.dump(annotator_json, open(self.annotator_json_fn, "w"))
        else:
            json_data = json.load(open(json_fn, "r"))
            json_data[self.annotation_field] = annotation_value
            json_data['annotator'] = self.annotator
            json.dump(json_data, open(json_fn, "w"))

        self.cleaning(unique_id)

    @property
    def new_annotator_rating(self):
        """
        A boolean property that is set to False after it is accessed
        """
        out = self._new_annotator_rating and len(self._annotator_rating) > 0
        self._new_annotator_rating = False
        return out

    @property
    def annotator_rating(self):
        """
        The last value of self._annotator_rating
        """
        return self._annotator_rating[-1]

    @annotator_rating.setter
    def annotator_rating(self, x):
        """
        Sets new_annotator_rating to True and prints it in the console
        """
        self._annotator_rating.append(x)
        self._new_annotator_rating = True
        LOGGER.info(
            f">>>>>>>>>>>>>>>>>>> New annotator rating: {x} <<<<<<<<<<<<<<<<<<"
        )

    def update_rating(self, data, annotator):
        """
        Update the rating computed for this annotator in respect to itself and
        to other annotators

        MUST BE REVISED!
        """
        if annotator not in data:
            return
        # computing self-correlation
        L = min(len(i) for i in data[annotator])
        if L > 1:
            self_data = [i[:L] for i in data[annotator]]
            r, _ = spearmanr(self_data, self_data, axis=0)
            if np.any(np.isnan(r)):
                self_r = 1.0
            else:
                self_r = r[np.tril_indices(r.shape[0])].mean()
        else:
            return

        annotator_indices = {}
        inter_data = []
        idx = 0
        for ann, vals in data.items():
            L = min(len(i) for i in data[ann])
            if L <= 0:
                continue
            # average annotation for each blob
            annotator_data = np.mean([i[:L] for i in data[ann]], axis=1)
            inter_data.append(annotator_data)
            annotator_indices[ann] = slice(idx, L)
            idx += L

        # how much this annotator average is different from the average
        # annotator
        inter_r, _ = spearmanr(np.mean(self_data, axis=1),
                               np.mean(inter_data, axis=0))
        if np.any(np.isnan(inter_r)):
            inter_r = 1.0
        self.annotator_rating = f"{round((self_r + inter_r) / 2 * 100)}%"
