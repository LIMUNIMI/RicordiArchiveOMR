from tqdm import tqdm
from collections import defaultdict
import json
from pprint import pprint
from joblib import Parallel, delayed
import toml
from pathlib import Path


def check_blob_jsons():

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
