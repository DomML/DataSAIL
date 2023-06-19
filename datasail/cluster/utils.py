import os
from typing import Tuple, List, Dict, Callable

import numpy as np
from matplotlib import pyplot as plt

from datasail.reader.utils import DataSet
from datasail.settings import LOGGER


def cluster_param_binary_search(
        dataset: DataSet,
        init_args: Tuple,
        threads: int,
        min_args: Tuple,
        max_args: Tuple,
        trial: Callable,
        args2str: Callable,
        gen_args: Callable,
        log_dir: str,
) -> Tuple[List[str], Dict[str, str], np.ndarray]:
    def args2log(x: Tuple):
        """
        Compute the name of the log file based on the provided arguments.

        Args:
            x: Arguments used in the run we want to store the results for

        Returns:
            Path to the file to write the execution log to
        """
        return None if log_dir is None else os.path.join(
            f"{dataset.get_name()}_{trial.__name__[:-6]}_{args2str(x).replace('-', '').replace(' ', '_')}.log"
        )

    # cluster with the initial arguments
    cluster_names, cluster_map, cluster_sim = trial(dataset, args2str(init_args), threads, args2log(init_args))
    num_clusters = len(cluster_names)
    LOGGER.info(f"First round of clustering found {num_clusters} clusters for {len(dataset.names)} samples.")

    # there are too few clusters, rerun with maximal arguments which has to result in every sample becomes a cluster
    if num_clusters <= 10:
        min_args = init_args
        min_clusters = num_clusters
        min_cluster_names, min_cluster_map, min_cluster_sim = cluster_names, cluster_map, cluster_sim
        max_cluster_names, max_cluster_map, max_cluster_sim = dataset.names, dict(
            (n, n) for n in dataset.names), np.zeros((len(dataset.names), len(dataset.names)))
        max_clusters = len(max_cluster_names)
        LOGGER.info(f"Second round of clustering found {max_clusters} clusters for {len(dataset.names)} samples.")

    # if the number of clusters ranges in a good window, return the result
    elif 10 < num_clusters <= 100:
        return cluster_names, cluster_map, cluster_sim

    # too many clusters have been found, rerun the clustering with minimal arguments to find the lower bound of clusters
    else:
        max_args = init_args
        max_clusters = num_clusters
        max_cluster_names, max_cluster_map, max_cluster_sim = cluster_names, cluster_map, cluster_sim
        min_cluster_names, min_cluster_map, min_cluster_sim = trial(dataset, args2str(min_args), threads,
                                                                    args2log(min_args))
        min_clusters = len(min_cluster_names)
        LOGGER.info(f"Second round of clustering found {min_clusters} clusters for {len(dataset.names)} samples.")

    # if the minimal number of clusters is in the target window, return them
    if 10 < min_clusters <= 100:
        return min_cluster_names, min_cluster_map, min_cluster_sim

    # if the maximal number of clusters is in the target window, return them
    if 10 < max_clusters <= 100:
        return max_cluster_names, max_cluster_map, max_cluster_sim

    # if the maximal number of clusters is still less than the lower bound of the window, report and warn
    if max_clusters < 10:
        LOGGER.warning(f"{trial.__name__[:-6]} cannot optimally cluster the data. The maximal number of clusters is "
                       f"{max_clusters}.")
        return max_cluster_names, max_cluster_map, max_cluster_sim

    # if the minimal number of clusters is still more than the upper bound of the window, report and warn
    if 100 < min_clusters:
        LOGGER.warning(f"{trial.__name__[:-6]} cannot optimally cluster the data. The minimal number of clusters is "
                       f"{min_clusters}.")
        return min_cluster_names, min_cluster_map, min_cluster_sim

    # for 8 rounds, apply binary search on the variable parameter space and try to hit the target window
    iteration_count = 0
    while True:
        iteration_count += 1
        args = gen_args(min_args, max_args)
        cluster_names, cluster_map, cluster_sim = trial(dataset, args2str(args), threads, args2log(args))
        num_clusters = len(cluster_names)
        LOGGER.info(f"Next round of clustering ({iteration_count + 2}.) "
                    f"found {num_clusters} clusters for {len(dataset.names)} samples.")
        if num_clusters <= 10 and iteration_count < 8:
            min_args = args
        elif 10 < num_clusters <= 100 or iteration_count >= 8:
            return cluster_names, cluster_map, cluster_sim
        else:
            max_args = args


def heatmap(matrix: np.ndarray, output_file: str) -> None:
    """
    Create a heatmap from a numpy array and two lists of labels.

    Args:
        matrix: A 2D numpy array of shape (M, N).
        output_file: Filename to store the matrix in.
    """
    fig, ax = plt.subplots()
    im = ax.imshow(matrix)
    ax.figure.colorbar(im, ax=ax)
    fig.tight_layout()
    plt.savefig(output_file)
    plt.clf()
