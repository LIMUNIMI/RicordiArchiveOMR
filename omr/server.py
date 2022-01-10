from pathlib import Path

import toml
from flask import Flask, request

from .image_manager import ImageManager

app = Flask(__name__, static_url_path='/static', root_path='.')

config = toml.load(open('./config.toml'))
# settings
s = config['data_entry']
BLOB_PATTERN = Path(
    config['preprocessing']['blob_dir']).glob("**/*_blob*.json")
ORIGINAL_IN_PARTS = len(Path(config['preprocessing']['input_dir']).parts)
IMAGE_MANAGER = ImageManager(BLOB_PATTERN,
                             s["annotation_field"],
                             s["annotator"],
                             control_length=s["control_length"],
                             control_freq=s["control_freq"],
                             static_dir='./static')


def _cc(x):
    return hex(255 - int(x, 16))[2:].zfill(2)


def get_complement_color(c):
    return f"{_cc(c[:2])}{_cc(c[2:4])}{_cc(c[4:])}"


def get_spaced_colors(n):
    max_value = 2**24 - 1
    interval = int(max_value / n)
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
        out += f'<input style="background-color:#{colors[i][0]};color:#{colors[i][1]};" type="submit" name="{name}" value="{value}" />'

    return out


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # save annotation
        annotation_value = s["annotation_values"][request.form[
            s["annotation_field"]]]
        id = request.form["id"]
        is_control = request.form["is_control"] == "True"
        IMAGE_MANAGER.save_annotation(id, is_control, annotation_value)

    # get next image
    try:
        blob_id, is_control, big_blob_path, partiture_path, in_parts = next(
            IMAGE_MANAGER)
        in_parts = in_parts[ORIGINAL_IN_PARTS:ORIGINAL_IN_PARTS + 2]
        from_ = f"This image is from <i><b>{in_parts[0]}</b>, {in_parts[1]}</i>"
        # blob = f'<img src="{blob_path}" height=200px/>'
        big_blob = f'<img src="{big_blob_path}" height=400px/>'
        partiture = f'<a href="{partiture_path}" target="_blank">Vedi la pagina originale</a>'

        d = []
        for v in s["annotation_values"].keys():
            d.append((s["annotation_field"], v))
        controllers = get_input_tags(d)

    except StopIteration:
        big_blob = "<h2>Ended!</h2>"
        partiture = ""
        from_ = ""
        blob_id = -1
        is_control = False
        controllers = ""
        # <input style="background-color:#000095;" type="submit" name="{s['annotation_field']}" value="Rilevante" />
        # <input style="background-color:#a66c00;" type="submit" name="{s['annotation_field']}" value="Irrilevante" />

    # return the page
    return f"""
        <div id="content">
            <h1>Archivio Ricordi ASL 2022</h1>
            <h3>La seguente immagine nel rettangolo rosso rappresenta un segno musicale rilevante?</h3>
            <p>
                {from_}
            </p>
            <p>
                {big_blob}
            </p>
            <p>

                <form action="" method="post">
                    <input type="hidden" type="submit" name="id" value="{blob_id}" />
                    <input type="hidden" type="submit" name="is_control" value="{is_control}" />
                    {controllers}
                </form>
            </p>
            <p>
                {partiture}
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
    waitress.serve(app, port=s["port"])
