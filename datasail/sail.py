import os.path
from typing import Dict, List, Callable, Union, Generator

from datasail.parsers import parse_datasail_args
from datasail.reader.utils import DATA_INPUT, MATRIX_INPUT
from datasail.routine import datasail_main
from datasail.settings import *


def error(msg: str, error_code: int, cli: bool) -> None:
    """
    Print an error message with an individual error code to the commandline. Afterwards, the program is stopped.

    Args:
        msg: Error message
        error_code: Code of the error to identify it
        cli: boolean flag indicating that this program has been started from commandline
    """
    LOGGER.error(msg)
    if cli:
        exit(error_code)
    else:
        raise ValueError(msg)


def validate_args(**kwargs) -> Dict[str, object]:
    """
    Validate the arguments given to the program.

    Notes:
        next error code: 26

    Args:
        **kwargs: Arguments in kwargs-format

    Returns:
        The kwargs in case something has been adjusted, e.g. splits normalization or naming
    """
    # create output directory
    output_created = False
    if kwargs[KW_OUTDIR] is not None and not os.path.isdir(kwargs[KW_OUTDIR]):
        output_created = True
        os.makedirs(kwargs[KW_OUTDIR], exist_ok=True)

    LOGGER.setLevel(VERB_MAP[kwargs[KW_VERBOSE]])
    LOGGER.handlers[0].setLevel(level=VERB_MAP[kwargs[KW_VERBOSE]])

    if kwargs[KW_OUTDIR] is not None:
        kwargs[KW_LOGDIR] = os.path.abspath(os.path.join(kwargs[KW_OUTDIR], "logs"))
        os.makedirs(kwargs[KW_LOGDIR], exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(kwargs[KW_LOGDIR], "general.log"))
        file_handler.setLevel(level=VERB_MAP[kwargs[KW_VERBOSE]])
        file_handler.setFormatter(FORMATTER)
        LOGGER.addHandler(file_handler)
    else:
        kwargs[KW_LOGDIR] = None

    if output_created:
        LOGGER.warning("Output directory does not exist, DataSAIL creates it automatically")

    LOGGER.info("Validating arguments")

    # check splits to be more than 1 and their fractions sum up to 1 and check the names
    if len(kwargs[KW_SPLITS]) < 2:
        error("Less then two splits required. This is no useful input, please check the input again.", 1,
              kwargs[KW_CLI])
    if kwargs[KW_NAMES] is None:
        kwargs[KW_NAMES] = [f"Split{x:03d}" for x in range(len(kwargs[KW_SPLITS]))]
    elif len(kwargs[KW_SPLITS]) != len(kwargs[KW_NAMES]):
        error("Different number of splits and names. You have to give the same number of splits and names for them.",
              2, kwargs[KW_CLI])
    elif len(kwargs[KW_NAMES]) != len(set(kwargs[KW_NAMES])):
        error("At least two splits will have the same name. Please check the naming of the splits again to have unique "
              "names", 24, kwargs[KW_CLI])
    kwargs[KW_SPLITS] = [x / sum(kwargs[KW_SPLITS]) for x in kwargs[KW_SPLITS]]

    # check search termination criteria
    if kwargs[KW_MAX_SEC] < 1:
        error("The maximal search time must be a positive integer.", 3, kwargs[KW_CLI])
    if kwargs[KW_MAX_SOL] < 1:
        error("The maximal number of solutions to look at has to be a positive integer.", 4, kwargs[KW_CLI])
    if kwargs[KW_THREADS] < 0:
        error("The number of threads to use has to be a non-negative integer.", 23, kwargs[KW_CLI])
    if kwargs[KW_THREADS] == 0:
        kwargs[KW_THREADS] = os.cpu_count()
    else:
        kwargs[KW_THREADS] = min(kwargs[KW_THREADS], os.cpu_count())

    # check the interaction file
    if kwargs[KW_INTER] is not None and isinstance(kwargs[KW_INTER], str) and not os.path.isfile(kwargs[KW_INTER]):
        error("The interaction filepath is not valid.", 5, kwargs[KW_CLI])

    # check the epsilon value
    if 1 < kwargs[KW_EPSILON] < 0:
        error("The epsilon value has to be a real value between 0 and 1.", 6, kwargs[KW_CLI])

    # check number of runs to be a positive integer
    if kwargs[KW_RUNS] < 1:
        error("The number of runs cannot be lower than 1.", 25, kwargs[KW_CLI])

    # check the input regarding the caching
    if kwargs[KW_CACHE] is not None and kwargs[KW_CACHE_DIR] is not None and isinstance(kwargs[KW_CACHE_DIR], str) and \
            not os.path.isdir(kwargs[KW_CACHE_DIR]):
        LOGGER.warning("Cache directory does not exist, DataSAIL creates it automatically")
        os.makedirs(kwargs[KW_CACHE_DIR], exist_ok=True)

    # syntactically parse the input data for the E-dataset
    if kwargs[KW_E_DATA] is not None and isinstance(kwargs[KW_E_DATA], str) and not os.path.exists(kwargs[KW_E_DATA]):
        error("The filepath to the E-data is invalid.", 7, kwargs[KW_CLI])
    if kwargs[KW_E_WEIGHTS] is not None and isinstance(kwargs[KW_E_WEIGHTS], str) and \
            not os.path.isfile(kwargs[KW_E_WEIGHTS]):
        error("The filepath to the weights of the E-data is invalid.", 8, kwargs[KW_CLI])
    if kwargs[KW_E_SIM] is not None and isinstance(kwargs[KW_E_SIM], str):
        if kwargs[KW_E_SIM].lower() not in SIM_ALGOS and not os.path.isfile(kwargs[KW_E_SIM]):
            error(f"The similarity metric for the E-data seems to be a file-input but the filepath is invalid.", 9,
                  kwargs[KW_CLI])
    if kwargs[KW_E_DIST] is not None and isinstance(kwargs[KW_E_DIST], str):
        if kwargs[KW_E_DIST].lower() not in DIST_ALGOS and not os.path.isfile(kwargs[KW_E_DIST]):
            error(f"The distance metric for the E-data seems to be a file-input but the filepath is invalid.", 10,
                  kwargs[KW_CLI])
    if 1 < kwargs[KW_E_MAX_SIM] < 0:
        error("The maximal similarity value for the E-data has to be a real value in [0,1].", 11, kwargs[KW_CLI])
    if 1 < kwargs[KW_E_MAX_DIST] < 0:
        error("The maximal distance value for the E-data has to be a real value in [0,1].", 12, kwargs[KW_CLI])

    # syntactically parse the input data for the F-dataset
    if kwargs[KW_F_DATA] is not None and isinstance(kwargs[KW_F_DATA], str) and not os.path.exists(kwargs[KW_F_DATA]):
        error("The filepath to the F-data is invalid.", 13, kwargs[KW_CLI])
    if kwargs[KW_F_WEIGHTS] is not None and isinstance(kwargs[KW_F_WEIGHTS], str) and not os.path.isfile(
            kwargs[KW_F_WEIGHTS]):
        error("The filepath to the weights of the F-data is invalid.", 14, kwargs[KW_CLI])
    if kwargs[KW_F_SIM] is not None and isinstance(kwargs[KW_F_SIM], str):
        if kwargs[KW_F_SIM].lower() not in SIM_ALGOS and not os.path.isfile(kwargs[KW_F_SIM]):
            error(f"The similarity metric for the F-data seems to be a file-input but the filepath is invalid.", 15,
                  kwargs[KW_CLI])
    if kwargs[KW_F_DIST] is not None and isinstance(kwargs[KW_F_DIST], str):
        if kwargs[KW_F_DIST].lower() not in DIST_ALGOS and not os.path.isfile(kwargs[KW_F_DIST]):
            error(f"The distance metric for the F-data seems to be a file-input but the filepath is invalid.", 16,
                  kwargs[KW_CLI])
    if 1 < kwargs[KW_F_MAX_SIM] < 0:
        error("The maximal similarity value for the F-data has to be a real value in [0,1].", 17, kwargs[KW_CLI])
    if 1 < kwargs[KW_F_MAX_DIST] < 0:
        error("The maximal distance value for the F-data has to be a real value in [0,1].", 18, kwargs[KW_CLI])

    return kwargs


def datasail(
        techniques: Union[str, List[str], Callable[..., List[str]], Generator[str, None, None]] = None,
        inter: Union[str, List[Tuple[str, str]], Callable[..., List[str]], Generator[str, None, None]] = None,
        max_sec: int = 100,
        max_sol: int = 1000,
        verbose: str = "W",
        splits: List[float] = None,
        names: List[str] = None,
        epsilon: float = 0.05,
        runs: int = 1,
        solver: str = SOLVER_SCIP,
        cache: bool = False,
        cache_dir: str = None,
        e_type: str = None,
        e_data: DATA_INPUT = None,
        e_weights: DATA_INPUT = None,
        e_sim: MATRIX_INPUT = None,
        e_dist: MATRIX_INPUT = None,
        e_args: str = "",
        e_max_sim: float = 1.0,
        e_max_dist: float = 1.0,
        f_type: str = None,
        f_data: DATA_INPUT = None,
        f_weights: DATA_INPUT = None,
        f_sim: MATRIX_INPUT = None,
        f_dist: MATRIX_INPUT = None,
        f_args: str = "",
        f_max_sim: float = 1.0,
        f_max_dist: float = 1.0,
        threads: int = 1,
) -> Tuple[Dict, Dict, Dict]:
    """
    Entry point for the package usage of DataSAIL.

    Args:
        techniques: List of techniques to split based on
        inter: Filepath to a TSV file storing interactions of the e-entities and f-entities.
        max_sec: Maximal number of seconds to take for optimizing a found solution.
        max_sol: Maximal number of solutions to look at when optimizing.
        verbose: Verbosity level for logging.
        splits: List of splits, have to add up to one, otherwise scaled accordingly.
        names: List of names of the splits.
        epsilon: Fraction by how much the provided split sizes may be exceeded
        runs: Number of runs to perform per split. This may introduce some variance in the splits.
        solver: Solving algorithm to use.
        cache: Boolean flag indicating to store or load results from cache.
        cache_dir: Directory to store the cache in if not the default location.
        e_type: Data format of the first batch of data
        e_data: Data file of the first batch of data
        e_weights: Weighting of the datapoints from e_data as TSV format
        e_sim: Similarity measure to apply for the e-data
        e_dist: Distance measure to apply for the e-data
        e_args: Additional arguments for the tools in e_sim or e_dist
        e_max_sim: Maximal similarity of two entities in different splits
        e_max_dist: Maximal distance of two entities in the same split
        f_type: Data format of the second batch of data
        f_data: Data file of the second batch of data
        f_weights: Weighting of the datapoints from f-data as TSV format
        f_sim: Similarity measure to apply for the f-data
        f_dist: Distance measure to apply for the f-data
        f_args: Additional arguments for the tools in f_sim or f-dist
        f_max_sim: Maximal similarity of two f-entities in different splits
        f_max_dist: Maximal distance of two f-entities in the same split
        threads: number of threads to use for one CD-HIT run

    Returns:
        Three dictionaries mapping techniques to another dictionary. The inner dictionary maps input id to their splits.
    """
    kwargs = validate_args(
        output=None, techniques=techniques, inter=inter, max_sec=max_sec, max_sol=max_sol, verbosity=verbose,
        splits=splits, names=names, epsilon=epsilon, runs=runs, solver=solver, cache=cache,
        cache_dir=cache_dir, e_type=e_type, e_data=e_data, e_weights=e_weights, e_sim=e_sim, e_dist=e_dist,
        e_args=e_args, e_max_sim=e_max_sim, e_max_dist=e_max_dist, f_type=f_type, f_data=f_data, f_weights=f_weights,
        f_sim=f_sim, f_dist=f_dist, f_args=f_args, f_max_sim=f_max_sim, f_max_dist=f_max_dist, threads=threads,
        cli=False,
    )
    return datasail_main(**kwargs)


def sail(args=None, **kwargs) -> None:
    """
    Entry point for the CLI tool. Invocation routine of DataSAIL. Here, the arguments are validated and the main
    routine is invoked.
    """
    if kwargs is None or len(kwargs) == 0:
        kwargs = parse_datasail_args(args or sys.argv[1:])
    kwargs[KW_CLI] = True
    kwargs = validate_args(**kwargs)
    datasail_main(**kwargs)
