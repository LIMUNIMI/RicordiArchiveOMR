from pathlib import Path

import toml
import numpy as np
from flask import Flask, request

from .image_manager import ImageManager, EndedHistoryException

app = Flask(__name__, static_url_path='/static', root_path='.')

config = toml.load(open('./config.toml'))
# settings
s = config['data_entry']
BLOB_JSONS = list(
    Path(config['preprocessing']['blob_dir']).glob("**/*_blob*.json"))

ORIGINAL_IN = Path(config['preprocessing']['input_dir'])
ORIGINAL_IN_PARTS = len(ORIGINAL_IN.parts)
IMAGE_MANAGER = ImageManager(BLOB_JSONS,
                             s["annotation_field"],
                             s["annotator"],
                             control_length=s["control_length"],
                             control_freq=s["control_freq"],
                             static_dir='./static')
RNG = np.random.default_rng(1995)


def _cc(x):
    return hex(255 - int(x, 16))[2:].zfill(2)


def get_complement_color(c):
    return f"{_cc(c[:2])}{_cc(c[2:4])}{_cc(c[4:])}"


def get_spaced_colors(n):
    max_value = 2**8
    interval = round(max_value / n)
    colors = []
    for c in range(0, max_value, interval):
        colors.append(
            (hex(c)[2:].zfill(6), get_complement_color(hex(c)[2:].zfill(6))))

    return colors


def get_input_tags(name_val_pairs, sep=""):
    """
    Returns an html string containing `<input />` tags with equal-spaced
    background color.

    `name` and `value` field are filled according to `name_val_dict`

    Each `<input />` is separated by `sep`.
    """
    out = ""
    L = len(name_val_pairs)
    colors = get_spaced_colors(L)
    for i, (name, value) in enumerate(name_val_pairs):
        out += f'<input style="background-color:#{colors[i][0]};color:#{colors[i][1]};" type="submit" name="{name}" value="{value}" />' + sep

    return out


@app.route("/", methods=['GET', 'POST'])
def home():
    """
    Looks for the next image and returns the web-page. If the request is a
    post, it also saves the annotation
    """
    if request.method == 'POST':
        # save annotation
        save_annotation()
    return make_page(None)


@app.route("/<int:idx>", methods=['GET'])
def hist(idx):
    """
    Looks for the next image and returns the web-page. If the request is a
    post, it also save the annotation
    If `IMAGE_MANAGER` has a new rating, it also adds a screen to communicate
    it.
    """
    return make_page(idx)


def save_annotation():
    annotation_value = s["annotation_values"][request.form[
        s["annotation_field"]]]
    json_fn = ORIGINAL_IN / request.form["json_fn"]
    is_control = request.form["is_control"] == "True"
    unique_id = request.form["unique_id"]
    IMAGE_MANAGER.save_annotation(json_fn, is_control, annotation_value,
                                  unique_id)


def make_page(idx=None):
    """
    Asks an image to `IMAGE_MANAGER`. If `idx` is `None`, it uses the next
    available image, otherwise it serves the image in the history at the `-idx`
    index.

    If `IMAGE_MANAGER` has a new rating, it also add a screen to communicate it.

    The served page has:
    * a title
    * an image
    * a form that submits to the home
    * a link to the full page
    * an optional div with the user rating
    """
    if idx is None or idx <= 1:
        arrow_left = '<a href="/2"><i class="arrow left"></i></a>'
        arrow_right = '<a style="visibility:hidden;"><i class="arrow right"></i></a>'
    else:
        arrow_left = f'<a href="/{idx+1}"><i class="arrow left"></i></a>'
        arrow_right = f'<a href="/{idx-1}"><i class="arrow right"></i></a>'
    try:
        json_fn, is_control, unique_id, in_parts = IMAGE_MANAGER.ask(idx)
        # the json_fn shouldn't be an absolute path, otherwise the client could
        # overwrite any file in the system
        json_fn = Path(json_fn).relative_to(ORIGINAL_IN)
        in_parts = in_parts[ORIGINAL_IN_PARTS:ORIGINAL_IN_PARTS + 2]
        from_ = f"Questa immagine proviene da <i><b>{in_parts[0]}</b>, {in_parts[1]}</i>"
        big_blob_path, partiture_path = IMAGE_MANAGER.get_filenames(unique_id)
        big_blob = f'<img src="{big_blob_path}" height=400px/>'
        partiture = f'<a href="{partiture_path}" target="_blank">Vedi la pagina originale</a>'

        d = []
        for v in s["annotation_values"].keys():
            d.append((s["annotation_field"], v))
        controllers = get_input_tags(d)

    except Exception as e:
        if type(e) is StopIteration:
            big_blob = "<h2>L'archivio Ricordi è finito!</h2>"
            arrow_right = '<a style="visibility:hidden;"><i class="arrow right"></i></a>'
        elif type(e) is EndedHistoryException:
            big_blob = "<h2>È finita la storia delle immagini!</h2>"
            arrow_left = '<a style="visibility:hidden;"><i class="arrow left"></i></a>'
        else:
            raise e

        partiture = ""
        from_ = ""
        json_fn = -1
        is_control = False
        controllers = ""
        unique_id = ""

    if IMAGE_MANAGER.new_annotator_rating:
        annotated = IMAGE_MANAGER.current_normal_idx + 1
        ratio = annotated / len(IMAGE_MANAGER.normal_jsons) * 100
        new_rating = IMAGE_MANAGER.annotator_rating
        gif = RNG.choice(list(Path('./static').glob("*.gif")))
        rating_div = f"""
            <div class="rating" id="rating-background">
                <div class="rating" id="rating-text">
                    <img src="{gif}" height="400px"/>
                    <h1>Abbiamo calcolato per te un nuovo punteggio!</h1>
                    Abbiamo stimato che le tue annotazioni sono corrette al
                    <h3>{new_rating}</h3>
                    <!--
                    Hai annotato il
                    <h3>{ratio}%</h3>
                    delle immagini ({annotated} immagini).
                    -->
                    <br/>
                    <button id="rating-button" onclick="document.getElementById('rating-background').hidden = true;">Continua</button>
                </div>
            </div>
        """
    else:
        rating_div = ""

    # return the page
    return f"""
        {rating_div}
        <div id="content">
            <h1>Archivio Ricordi ASL 2022</h1>
            <h3>La seguente immagine nel rettangolo rosso a quale categoria può essere attribuita?</h3>
            <p>
                {from_}
            </p>
            <p>
                {big_blob}
            </p>
            <p>
                {partiture}
            </p>
        </div>
        <div id="arrows">
            {arrow_left}
            {arrow_right}
        </div>
        <form action="/" method="post">
            <input type="hidden" type="submit" name="json_fn" value="{json_fn}" />
            <input type="hidden" type="submit" name="is_control" value="{is_control}" />
            <input type="hidden" type="submit" name="unique_id" value="{unique_id}" />
            {controllers}
        </form>
        <style>
            input {{
                color: white;
                border: 1px #0264fc solid;
                height: 50px;
                padding: 5px;
                opacity: 0.6;
                transition: 0.3s;
            }}

            input:hover, #rating-button:hover {{
                opacity: 1;
                cursor: pointer;
            }}

            body {{
                position: relative;
                height: 100%;
                width: 100%;
            }}

            #content, .rating {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
            }}

            #rating-background {{
                z-index: 100;
                background-color: rgba(54, 255, 104, 0.9);
                width: 100%;
                height: 100%;
            }}

            #rating-button {{
                background: #ff8b46;
                border: none;
                width: 20%;
                height: 50px;
                color: #ffe4d5;
                opacity: 1;
            }}

            form {{
                position: fixed;
                top: 50%;
                left: 5%;
                width: 0px;
                margin: 0px;
                padding: 0px;
                transform: translate(0%, -50%);
            }}

            #arrows {{
                position: fixed;
                top: 50%;
                right: 7.5%;
                transform: translate(-50%, 0%);
            }}

            .arrow {{
                border: solid black;
                border-width: 0 20px 20px 0;
                display: inline-block;
                padding: 30px;
                margin-bottom: 20px;
                margin-top: 20px;
            }}

            .right {{
                transform: rotate(-45deg);
                -webkit-transform: rotate(-45deg);
            }}

            .left {{
                transform: rotate(135deg);
                -webkit-transform: rotate(135deg);
            }}

        </style>
    """


def run():
    import waitress
    waitress.serve(app, port=s["port"])
