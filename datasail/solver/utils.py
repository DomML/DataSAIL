import functools
import logging
import operator
import sys
from typing import List, Tuple, Collection, Dict, Optional

import cvxpy
import numpy as np

from datasail.settings import LOGGER


def compute_limits(epsilon: float, total: int, splits: List[float]) -> Tuple[List[float], List[float]]:
    """
    Compute the lower and upper limits for the splits based on the total number of interactions and the epsilon.

    Args:
        epsilon: epsilon to use
        total: total number of interactions
        splits: list of splits

    Returns:
        lower and upper limits for the splits
    """
    return [int(split * (1 + epsilon) * total) for split in splits], \
        [int(split * (1 - epsilon) * total) for split in splits]


def inter_mask(
        e_entities: List[str],
        f_entities: List[str],
        inter: Collection[Tuple[str, str]],
) -> np.ndarray:
    """
    Compute an interaction mask, i.e. an adjacency matrix from the list of interactions.
    Compute adjacency matrix by first compute mappings from entity names to their index and then setting the
    individual interactions to 1.

    Args:
        e_entities: Entities in e-dataset
        f_entities: Entities in f-dataset
        inter: List of interactions between entities in e-dataset and entities in f-dataset

    Returns:
        Adjacency matrix based on the list of interactions
    """
    output = np.zeros((len(e_entities), len(f_entities)))
    d_map = dict((e, i) for i, e in enumerate(e_entities))
    p_map = dict((f, i) for i, f in enumerate(f_entities))
    for e, f in inter:
        output[d_map[e], p_map[f]] = 1
    return output


class LoggerRedirect:
    def __init__(self, logfile_name):
        """
        Initialize this redirection module to be used to pipe messages to stdout to some file.
        Args:
            logfile_name: Filename to write stdout logs to instead of the console
        """
        if logfile_name is None:
            self.silent = True
            return
        self.file_handler = logging.FileHandler(logfile_name)
        self.old_stdout = sys.stdout
        self.disabled = {}
        self.silent = False

    def __enter__(self):
        """
        Remove the stream from all loggers that print to stdout.
        """
        if self.silent:
            return
        for name, logger in logging.root.manager.loggerDict.items():
            if isinstance(logger, logging.Logger) and len(logger.handlers) > 0:
                for handler in logger.handlers:
                    if not hasattr(handler, "stream"):
                        continue
                    if handler.stream.name == "<stdout>":
                        if name not in self.disabled:
                            self.disabled[name] = []
                        self.disabled[name].append(handler)
                if name in self.disabled:
                    for handler in self.disabled[name]:
                        logger.removeHandler(handler)
                logger.addHandler(self.file_handler)
        sys.stdout = self.file_handler.stream

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Re-instantiate all loggers with their streams.

        Args:
            exc_type: ignored
            exc_val: ignored
            exc_tb: ignored
        """
        if self.silent:
            return
        for name, handlers in self.disabled.items():
            logger = logging.root.manager.loggerDict[name]
            logger.removeHandler(self.file_handler)
            for handler in handlers:
                logger.addHandler(handler)
        sys.stdout = self.old_stdout


def solve(loss, constraints: List, max_sec: int, solver: str, log_file: str) -> Optional[cvxpy.Problem]:
    """
    Minimize the loss function based on the constraints with the timelimit specified by max_sec.

    Args:
        loss: Loss function to minimize
        constraints: Constraints that have to hold
        max_sec: Maximal number of seconds to optimize the initial solution
        solver: Solving algorithm to use to solve the formulated program
        log_file: File to store the detailed log from the solver to

    Returns:
        The problem object after solving. None if the problem could not be solved.
    """
    problem = cvxpy.Problem(cvxpy.Minimize(loss), constraints)
    LOGGER.info(f"Start solving with {solver}")
    LOGGER.info(f"The problem has {sum([functools.reduce(operator.mul, v.shape, 1) for v in problem.variables()])} variables "
                f"and {sum([functools.reduce(operator.mul, c.shape, 1) for c in problem.constraints])} constraints.")

    if solver == "MOSEK":
        solve_algo = cvxpy.MOSEK
        kwargs = {"mosek_params": {
            "MSK_DPAR_OPTIMIZER_MAX_TIME": max_sec,
            "MSK_IPAR_NUM_THREADS": 14,
            # "MSK_IPAR_OPTIMIZER": "conic",
        }}
    else:
        solve_algo = cvxpy.SCIP
        kwargs = {"scip_params": {"limits/time": max_sec}}
    with LoggerRedirect(log_file):
        try:
            problem.solve(
                solver=solve_algo,
                qcp=True,
                verbose=True,
                **kwargs,
            )

            LOGGER.info(f"{solver} status: {problem.status}")
            LOGGER.info(f"Solution's score: {problem.value}")

            if "optimal" not in problem.status:
                LOGGER.warning(
                    f'{solver} cannot solve the problem. Please consider relaxing split restrictions, '
                    'e.g., less splits, or a higher tolerance level for exceeding cluster limits.'
                )
                return None
            return problem
        except KeyError:
            LOGGER.warning(f"Solving failed for {''}. Please use try another solver or update your python version.")
            return None


def sample_categorical(
        inter: List[Tuple[str, str]],
        splits: List[float],
        names: List[str],
) -> Dict[Tuple[str, str], str]:
    """
    Sample interactions randomly into splits. This is the random split. It relies on the idea of categorical sampling.

    Args:
        inter: List of interactions to split
        splits: List of splits given by their relative size
        names: List of names given by their relative size

    Yields:
        Chunks of interactions in order of the splits
    """
    np.random.shuffle(inter)

    def gen():
        for index in range(len(splits) - 1):
            yield inter[int(sum(splits[:index]) * len(inter)):int(sum(splits[:(index + 1)]) * len(inter))]
        yield inter[int(sum(splits[:-1]) * len(inter)):]

    output = {}
    for i, split in enumerate(gen()):
        output.update({(d, p): names[i] for d, p in split})
    return output
