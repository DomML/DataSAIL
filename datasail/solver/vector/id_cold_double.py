from typing import Optional, Tuple, List, Set, Dict

import cvxpy
import numpy as np
from datasail.settings import LOGGER

from datasail.solver.utils import solve, inter_mask
from datasail.solver.vector.utils import interaction_constraints


def solve_icd_bqp(
        e_entities: List[str],
        f_entities: List[str],
        inter: Set[Tuple[str, str]],
        epsilon: float,
        splits: List[float],
        names: List[str],
        max_sec: int,
        max_sol: int,
        solver: str,
        log_file: str,
) -> Optional[Tuple[Dict[Tuple[str, str], str], Dict[object, str], Dict[object, str]]]:
    """
    Solve identity-based double-cold splitting using disciplined quasi-convex programming and binary quadratic
    programming.

    Args:
        e_entities: List of entity names to split in e-dataset
        f_entities: List of entity names to split in f-dataset
        inter: List of interactions
        epsilon: Additive bound for exceeding the requested split size
        splits: List of split sizes
        names: List of names of the splits in the order of the splits argument
        max_sec: Maximal number of seconds to take when optimizing the problem (not for finding an initial solution)
        max_sol: Maximal number of solution to consider
        solver: Solving algorithm to use to solve the formulated program
        log_file: File to store the detailed log from the solver to

    Returns:
        A list of interactions and their assignment to a split and two mappings from entities to splits, one for each
        dataset
    """
    inter_count = len(inter)
    inter_ones = inter_mask(e_entities, f_entities, inter)
    min_lim = [int((split - epsilon) * inter_count) for split in splits]
    max_lim = [int((split + epsilon) * inter_count) for split in splits]

    x_e = [cvxpy.Variable((len(e_entities), 1), boolean=True) for _ in range(len(splits))]
    x_f = [cvxpy.Variable((len(f_entities), 1), boolean=True) for _ in range(len(splits))]
    x_i = [cvxpy.Variable((len(e_entities), len(f_entities)), boolean=True) for _ in range(len(splits))]

    constraints = [
        cvxpy.sum([x[:, 0] for x in x_e]) == np.ones((len(e_entities))),
        cvxpy.sum([x[:, 0] for x in x_f]) == np.ones((len(f_entities))),
    ]
    constraints += [
        cvxpy.sum([x for x in x_i]) <= inter_ones,
    ]

    for s, split in enumerate(splits):
        constraints += [
            min_lim[s] <= cvxpy.sum(cvxpy.sum(cvxpy.multiply(inter_ones, x_i[s]), axis=0), axis=0),
            cvxpy.sum(cvxpy.sum(cvxpy.multiply(inter_ones, x_i[s]), axis=0), axis=0) <= max_lim[s],
        ] + interaction_constraints(e_entities, f_entities, inter, x_e, x_f, x_i, s)

    inter_loss = cvxpy.sum(cvxpy.sum(inter_ones - cvxpy.sum([x for x in x_i]), axis=0), axis=0) / inter_count
    LOGGER.info(f"#E: {len(e_entities)}")
    LOGGER.info(f"#F: {len(f_entities)}")
    LOGGER.info(f"#I: {len(inter)}")
    LOGGER.info(f"#S: {len(splits)}")
    LOGGER.info(f"#C: {len(constraints)}")
    problem = solve(inter_loss, constraints, max_sec, solver, log_file)

    # report the found solution
    output = ({}, dict(
        (e, names[s]) for s in range(len(splits)) for i, e in enumerate(e_entities) if x_e[s][:, 0][i].value > 0.1
    ), dict(
        (f, names[s]) for s in range(len(splits)) for j, f in enumerate(f_entities) if x_f[s][:, 0][j].value > 0.1
    ))
    for i, e in enumerate(e_entities):
        for j, f in enumerate(f_entities):
            if (e, f) in inter:
                for b in range(len(splits)):
                    if x_i[b][i, j].value > 0:
                        output[0][(e, f)] = names[b]
                if sum(x_i[b][i, j].value for b in range(len(splits))) == 0:
                    output[0][(e, f)] = "not selected"

    return output
