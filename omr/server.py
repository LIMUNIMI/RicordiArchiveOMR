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
IMAGE_MANAGER = ImageManager(BLOB_PATTERN,
                             s["annotation_field"],
                             s["annotator"],
                             control_length=s["control_length"],
                             control_freq=s["control_freq"],
                             static_dir='./static')

# @app.route('/<path:path>')
# def static_file(path):
#     __import__('ipdb').set_trace()
#     path = Path(path).name
#     return app.send_static_file(path)


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # save annotation
        annotation_value = s["annotation_values"][request.form[
            s["annotation_field"]]]
        IMAGE_MANAGER.save_annotation(annotation_value)

    # get next image
    try:
        blob_path, big_blob_path, partiture_path, parents = next(IMAGE_MANAGER)
        print(parents)
        blob = f'<img src="{blob_path}" height=200px/>'
        big_blob = f'<img src="{big_blob_path}" height=400px/>'
        partiture = f'<a href="{partiture_path}" target="_blank">Vedi la pagina originale</a>'
    except StopIteration:
        blob = "<h2>Ended!</h2>"
        big_blob = ""
        partiture = ""

    # return the page
    return f"""
        <div id="content">
            <h1>Archivio Ricordi ASL 2022</h1>
            <h3>La seguente immagine rappresenta un segno musicale rilevante?</h3>
            <p>
                {blob}
            </p>
            <p>

                <form action="" method="post">
                    <input style="background-color:#000095;" type="submit" name="{s['annotation_field']}" value="Rilevante" />
                    <input style="background-color:#a66c00;" type="submit" name="{s['annotation_field']}" value="Irrilevante" />
                </form>
            </p>
            <p>
                This is a larger view:<br/>
                {big_blob}
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

            <!--
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
            -->
        </style>
    """


def run():
    import waitress
    waitress.serve(app, port=s["port"])
