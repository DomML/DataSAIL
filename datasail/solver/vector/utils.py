from typing import List, Optional, Union, Tuple, Set

import cvxpy
import numpy as np
from cvxpy import Variable, Expression
from cvxpy.constraints.constraint import Constraint


def interaction_constraints(
        e_data: List[str],
        f_data: List[str],
        inter: Union[Set[Tuple[str, str]], np.ndarray],
        x_e: List[Variable],
        x_f: List[Variable],
        x_i: List[Variable],
        s: int
) -> List[Constraint]:
    """
    Define the constraints that two clusters are in the same split iff their interaction (if exists) is in that split.

    Args:
        e_data: Names of datapoints in the e-dataset
        f_data: Names of datapoints in the f-dataset
        inter: a set of interactions between pairs of entities
        x_e: List of variables for the e-dataset
        x_f: List of variables for the f-dataset
        x_i: List of variables for the interactions
        s: Current split to consider

    Returns:
        A list of cvxpy constraints
    """
    constraints = []
    for i, e1 in enumerate(e_data):
        for j, e2 in enumerate(f_data):
            if isinstance(inter, np.ndarray) or (e1, e2) in inter:
                constraints.append(x_i[s][i, j] >= (x_e[s][:, 0][i] + x_f[s][:, 0][j] - 1.5))
                constraints.append(x_i[s][i, j] <= (x_e[s][:, 0][i] + x_f[s][:, 0][j]) * 0.5)
                constraints.append(x_e[s][:, 0][i] >= x_i[s][i, j])
                constraints.append(x_f[s][:, 0][j] >= x_i[s][i, j])
    return constraints


def cluster_sim_dist_constraint(
        similarities: Optional[np.ndarray],
        distances: Optional[np.ndarray],
        threshold: np.ndarray,
        ones: np.ndarray,
        x: List[Variable],
        s: int
) -> List[Constraint]:
    """
    Define the constraints on similarities between samples in difference splits or distances of samples in the same
    split.

    Args:
        similarities: Similarity matrix of the data
        distances: Distance matrix of the data
        threshold: Threshold to apply
        ones: Vector to help in the computations
        x: List of variables for the dataset
        s: Split to consider

    Returns:
        A list of cvxpy constraints
    """
    if distances is not None:
        return cvxpy.multiply(
            cvxpy.maximum((x[s] @ ones) + cvxpy.transpose(x[s] @ ones) - (ones.T @ ones), 0), distances
        ) <= threshold
    return cvxpy.multiply(((x[s] @ ones) - cvxpy.transpose(x[s] @ ones)) ** 2, similarities) <= threshold


def cluster_sim_dist_objective(
        similarities: Optional[np.ndarray],
        distances: Optional[np.ndarray],
        ones: np.ndarray,
        weights: Union[np.ndarray, List[float]],
        x: List[Variable],
        splits: List[float]
) -> Expression:
    """
    Construct an objective function of the variables based on a similarity or distance matrix.

    Args:
        similarities: Similarity matrix of the dataset
        distances: Distance matrix of the dataset
        ones: Vector to help in the computations
        weights: weights of the entities
        x: Dictionary of indices and variables for the e-dataset
        splits: Splits as list of their relative size

    Returns:
        An objective function to minimize
    """
    if isinstance(weights, List):
        weights = np.array(weights)

    weight_matrix = weights.T @ weights

    if distances is not None:
        hit_matrix = cvxpy.sum([cvxpy.maximum((x[s] @ ones) + cvxpy.transpose(x[s] @ ones) - (ones.T @ ones), 0) for s in range(len(splits))])
        leak_matrix = cvxpy.multiply(hit_matrix, distances)
    else:
        hit_matrix = cvxpy.sum([((x[s] @ ones) - cvxpy.transpose(x[s] @ ones)) ** 2 for s in range(len(splits))])
        leak_matrix = cvxpy.multiply(hit_matrix, similarities)

    leak_matrix = cvxpy.multiply(leak_matrix, weight_matrix)
    # leakage = cvxpy.sum(leak_matrix) / cvxpy.sum(cvxpy.multiply(hit_matrix, weight_matrix))  # accurate computation
    return cvxpy.sum(leak_matrix)
