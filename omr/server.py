import json
import shutil
from pathlib import Path

import toml
import numpy as np
from flask import Flask, request

app = Flask(__name__)
random = np.random.default_rng(1992)


def read_annotation(fname, annotation_field):
    data = json.load(open(fname, "r"))
    if annotation_field in data:
        return data[annotation_field]
    else:
        return None


class ImageManager:
    """
    An iterator that provides the next image that must be annotated
    """

    def __init__(self,
                 blob_pattern,
                 annotation_field,
                 control_length=100,
                 control_freq=200):
        # shuffling blobs
        full_json_list = list(blob_pattern)
        random = np.random.default_rng(1992)
        random.shuffle(full_json_list)  # in-place...

        # splitting control set
        self.control_jsons = full_json_list[:control_length]
        self.normal_jsons = full_json_list[control_length:]

        # initializing fields
        self.current_normal_idx = 0
        self.current_control_idx = 0
        self.annotation_field = annotation_field
        self.control_freq = 200

    def __next__(self):
        """
        returns the next image path that should be annotated
        """
        # checking if we should provide a control json
        if random.random() < 1 / self.control_freq:
            # pick next control blob
            if self.current_control_idx > len(self.control_jsons):
                self.current_control_idx = 0
            self.current_json = self.control_jsons[self.current_control_idx]
            self.current_control_idx += 1
        else:
            # looking for the first json not annotated
            FOUND = False
            for idx, json_fname in enumerate(
                    self.normal_jsons[self.current_control_idx:]):
                if read_annotation(json_fname, self.annotation_field) is None:
                    FOUND = True
                    self.current_normal_idx = idx
                    self.current_json = json_fname
                    break
            if not FOUND:
                raise StopIteration

        # copy the image in a place visible to the server
        img_path = read_annotation(self.current_json, "path")
        suffix = Path(img_path).suffix
        served_img = Path(__file__).parent.parent / ("served_img" + suffix)
        shutil.copyfile(img_path, served_img)
        return served_img

    def save_annotation(self, annotation_value):
        json_data = json.load(open(self.current_json, "r"))
        json_data[self.annotation_field] = annotation_value
        json.dump(json_data, open(self.current_json, "w"))


conf = toml.load(open('./config.toml'))
__port = conf['data_entry']['port']
__annotation_values = conf['data_entry']['annotation_values']
__annotation_field = conf['data_entry']['annotation_field']
__control_length = conf['data_entry']['control_length']
__control_freq = conf['data_entry']['control_freq']
__blob_pattern = Path(conf['preprocessing']['blob_dir']).glob("**/*.json")
__image_manager = ImageManager(__blob_pattern, __annotation_field,
                               __control_length, __control_freq)


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # save annotation
        annotation_value = __annotation_values[
            request.form[__annotation_field]]
        __image_manager.save_annotation(annotation_value)

    # get next image
    try:
        img_path = next(__image_manager)
        img = f'<img src="{img_path}" height=300px/>'
    except StopIteration:
        img = "<h2>Ended!</h2>"

    # return the page
    return f"""
        <div id="content">
            <h1>Archivio Ricordi ASL 2022</h1>
            <h3>La seguente immagine rappresenta un segno musicale rilevante?</h3>
            <p>
                {img}
            </p>
            <p>

                <form action="" method="post">
                    <input style="background-color:#000095;" type="submit" name="{{__annotation_field}}" value="Rilevante" />
                    <input style="background-color:#a66c00;" type="submit" name="{{__annotation_field}}" value="Irrilevante" />
                </form>
            </p>
        </div>
        <style>
            input {{
                color: white;
                border: none;
                height: 50px;
                padding: 5px;
                opacity: 0.6;
                transition: 0.3s;
            }}

            input:hover {{
                opacity: 1;
                cursor: pointer;
            }}

            body {{
                display: table;
                text-align: center;
                height: 100%;
                width: 100%;
            }}

            #content {{
                display: table-cell;
                vertical-align: middle;
            }}
        </style>
    """


def run():
    import waitress
    waitress.serve(app, port=__port)
