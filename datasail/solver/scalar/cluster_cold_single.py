from typing import List, Optional, Dict, Union

import numpy as np
from datasail.settings import LOGGER

from datasail.solver.scalar.utils import cluster_sim_dist_constraint, cluster_sim_dist_objective, \
    init_variables, sum_constraint
from datasail.solver.utils import solve


def solve_ccs_bqp(
        e_clusters: List[Union[str, int]],
        e_weights: List[float],
        e_similarities: Optional[np.ndarray],
        e_distances: Optional[np.ndarray],
        e_threshold: float,
        epsilon: float,
        splits: List[float],
        names: List[str],
        max_sec: int,
        max_sol: int,
        solver: str,
        log_file: str,
) -> Optional[Dict[str, str]]:
    """
    Solve cluster-based cold splitting using disciplined quasi-convex programming and binary quadratic programming.

    Args:
        e_clusters: List of cluster names to split
        e_weights: Weights of the clusters in the order of their names in e_clusters
        e_similarities: Pairwise similarity matrix of clusters in the order of their names
        e_distances: Pairwise distance matrix of clusters in the order of their names
        e_threshold: Threshold to not undergo when optimizing
        epsilon: Additive bound for exceeding the requested split size
        splits: List of split sizes
        names: List of names of the splits in the order of the splits argument
        max_sec: Maximal number of seconds to take when optimizing the problem (not for finding an initial solution)
        max_sol: Maximal number of solution to consider
        solver: Solving algorithm to use to solve the formulated program
        log_file: File to store the detailed log from the solver to

    Returns:
        Mapping from clusters to splits optimizing the objective function
    """
    LOGGER.warn("The usage of scalar solver is deprecated.")
    alpha = 0.01

    x_e = init_variables(len(splits), len(e_clusters))

    constraints = sum_constraint(x_e, len(e_clusters), len(splits))

    for s in range(len(splits)):
        var = sum(x_e[i, s] * e_weights[i] for i in range(len(e_clusters)))

        constraints += [
            int((splits[s] - epsilon) * sum(e_weights)) <= var,
            var <= int((splits[s] + epsilon) * sum(e_weights))
        ] + cluster_sim_dist_constraint(e_similarities, e_distances, e_threshold, len(e_clusters), x_e, s)

    size_loss = sum(
        (sum(x_e[i, s] * e_weights[i] for i in range(len(e_clusters))) - splits[s] * sum(e_weights)) ** 2
        for s in range(len(splits))
    )
    e_loss = cluster_sim_dist_objective(e_similarities, e_distances, len(e_clusters), e_weights, x_e, len(splits))

    problem = solve(alpha * size_loss + e_loss, constraints, max_sec, solver, log_file)

    if problem is None:
        return {}

    return {e: names[s] for s in range(len(splits)) for i, e in enumerate(e_clusters) if x_e[i, s].value > 0.1}
