import os
import shutil
from typing import Tuple, List, Dict

import numpy as np

from datasail.reader.utils import DataSet


def run_cdhit(dataset: DataSet) -> Tuple[List[str], Dict[str, str], np.ndarray]:
    cmd = f"mkdir cdhit && " \
          f"cd cdhit && " \
          f"cd-hit -i {os.path.join('..', dataset.location)} -o clusters"

    print(cmd)
    os.system(cmd)

    cluster_map = get_cdhit_map("cdhit/clusters.clstr")
    cluster_names = list(set(cluster_map.values()))
    cluster_sim = np.ones((len(cluster_names), len(cluster_names)))
    shutil.rmtree("cdhit")

    return cluster_names, cluster_map, cluster_sim


def get_cdhit_map(cluster_file: str) -> Dict[str, str]:
    mapping = {}
    rep = ""
    members = []
    with open(cluster_file, "r") as data:
        for line in data.readlines():
            line = line.strip()
            if line[0] == ">":
                if rep != "":
                    mapping[rep] = rep
                    for name in members:
                        mapping[name] = rep
                rep = ""
                members = []
            elif line[-1] == "*":
                rep = line.split(">")[1].split("...")[0]
            else:
                members.append(line.split(">")[1].split("...")[0])
    mapping[rep] = rep
    for name in members:
        mapping[name] = rep
    return mapping
