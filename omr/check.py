def check_blob_jsons():
    import json
    from pathlib import Path
    from pprint import pprint

    import toml
    from tqdm import tqdm
    from joblib import Parallel, delayed

    config = toml.load(open('./config.toml'))

    print("loading files...")
    files = list(
        Path(config['preprocessing']['blob_dir']).glob("**/*_blob*.json"))

    def _process(file):
        count = {}
        content = json.load(open(file))
        for c in content:
            if content[c] is not None:
                count[c] = 1
        return count

    res = Parallel(n_jobs=10)(delayed(_process)(file) for file in tqdm(files))

    count = {}
    for d in res:
        for k in d:
            if k in count:
                count[k] += d[k]
            else:
                count[k] = d[k]

    print("Number of files annotated for each field")
    pprint(count)
    print(f"Total number of files: {len(files)}")


def plot_normal_indices():
    import re
    import plotly.graph_objects as go

    regexp = re.compile(
        "(?P<date>^[\d\- :,]{23}).*[c|C]urrent_normal_idx: (?P<index>[0-9]+)/[0-9]+"
    )
    xx = []
    data = []
    with open("server.log") as f:
        for line in f:
            m = regexp.match(line)
            if m:
                data.append(int(m.group('index')))
                xx.append(str(m.group('date')))

    fig = go.Figure(data=go.Scatter(x=xx, y=data))
    fig.write_html("normal_indices.html")
