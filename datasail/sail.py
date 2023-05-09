import logging
import os.path
import sys
from typing import Dict, List, Tuple

from datasail.parsers import parse_cdhit_args, parse_mash_args, parse_mmseqs_args, DIST_ALGOS, SIM_ALGOS, \
    parse_datasail_args
from datasail.run import bqp_main
from datasail.settings import LOGGER, FORMATTER, VERB_MAP


def error(msg: str, error_code: int) -> None:
    """
    Print an error message with an individual error code to the commandline. Afterwards, the program is stopped.

    TODO: If run as CLI tool, exit with error code, else raise exception

    Args:
        msg: Error message
        error_code: Code of the error to identify it
    """
    LOGGER.error(msg)
    exit(error_code)


def validate_args(**kwargs) -> Dict[str, object]:
    """
    Validate the arguments given to the program.

    Notes:
        next error code: 25

    Args:
        **kwargs: Arguments in kwargs-format

    Returns:
        The kwargs in case something has been adjusted, e.g. splits have to transformed into sum=1-vector or naming
    """

    # create output directory
    output_created = False
    if kwargs["output"] is not None and not os.path.isdir(kwargs["output"]):
        output_created = True
        os.makedirs(kwargs["output"], exist_ok=True)

    LOGGER.setLevel(VERB_MAP[kwargs["verbosity"]])
    LOGGER.handlers[0].setLevel(level=VERB_MAP[kwargs["verbosity"]])

    if kwargs["output"] is not None:
        kwargs["logdir"] = os.path.abspath(os.path.join(kwargs["output"], "logs"))
        os.makedirs(kwargs["logdir"], exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(kwargs["logdir"], "general.log"))
        file_handler.setLevel(level=VERB_MAP[kwargs["verbosity"]])
        file_handler.setFormatter(FORMATTER)
        LOGGER.addHandler(file_handler)
    else:
        kwargs["logdir"] = None

    if output_created:
        LOGGER.warning("Output directory does not exist, DataSAIL creates it automatically")

    LOGGER.info("Validating arguments")

    # check splits to be more than 1 and their fractions sum up to 1 and check the names
    if len(kwargs["splits"]) < 2:
        error("Less then two splits required. This is no useful input, please check the input again.", error_code=1)
    if kwargs["names"] is None:
        kwargs["names"] = [f"Split{x:03d}" for x in range(len(kwargs["splits"]))]
    elif len(kwargs["splits"]) != len(kwargs["names"]):
        error("Different number of splits and names. You have to give the same number of splits and names for them.",
              error_code=2)
    elif len(kwargs["names"]) != len(set(kwargs["names"])):
        error("At least two splits will have the same name. Please check the naming of the splits again to have unique "
              "names", error_code=24)
    kwargs["splits"] = [x / sum(kwargs["splits"]) for x in kwargs["splits"]]

    # convert vectorized from the input question to the flag used in the code
    kwargs["vectorized"] = not kwargs["vectorized"]

    # check search termination criteria
    if kwargs["max_sec"] < 1:
        error("The maximal search time must be a positive integer.", error_code=3)
    if kwargs["max_sol"] < 1:
        error("The maximal number of solutions to look at has to be a positive integer.", error_code=4)
    if kwargs["threads"] < 0:
        error("The number of threads to use has to be a non-negative integer.", error_code=23)
    if kwargs["threads"] == 0:
        kwargs["threads"] = os.cpu_count()
    else:
        kwargs["threads"] = min(kwargs["threads"], os.cpu_count())

    # check the interaction file
    if kwargs["inter"] is not None and not os.path.isfile(kwargs["inter"]):
        error("The interaction filepath is not valid.", error_code=5)

    # check the epsilon value
    if 1 < kwargs["epsilon"] < 0:
        error("The epsilon value has to be a real value between 0 and 1.", error_code=6)

    # check the input regarding the caching
    if kwargs["cache"] and not os.path.isdir(kwargs["cache_dir"]):
        LOGGER.warning("Cache directory does not exist, DataSAIL creates it automatically")
        os.makedirs(kwargs["cache_dir"], exist_ok=True)

    # syntactically parse the input data for the E-dataset
    if kwargs["e_data"] is not None and not os.path.exists(kwargs["e_data"]):
        error("The filepath to the E-data is invalid.", error_code=7)
    if kwargs["e_weights"] is not None and not os.path.isfile(kwargs["e_weights"]):
        error("The filepath to the weights of the E-data is invalid.", error_code=8)
    if kwargs["e_sim"] is not None and kwargs["e_sim"].lower() not in SIM_ALGOS and not os.path.isfile(kwargs["e_sim"]):
        error(
            f"The similarity metric for the E-data seems to be a file-input but the filepath is invalid.", error_code=9
        )
    if kwargs["e_dist"] is not None and kwargs["e_dist"].lower() not in DIST_ALGOS and not os.path.isfile(
            kwargs["e_dist"]):
        error(
            f"The distance metric for the E-data seems to be a file-input but the filepath is invalid.", error_code=10
        )
    if kwargs["e_sim"] is not None and kwargs["e_sim"].lower() == "cdhit":
        validate_cdhit_args(kwargs["e_args"])
    if kwargs["e_sim"] is not None and kwargs["e_sim"].lower() == "mmseqs":
        validate_mmseqs_args(kwargs["e_args"])
    if kwargs["e_dist"] is not None and kwargs["e_dist"].lower() == "mash":
        validate_mash_args(kwargs["e_args"])
    if 1 < kwargs["e_max_sim"] < 0:
        error("The maximal similarity value for the E-data has to be a real value in [0,1].", error_code=11)
    if 1 < kwargs["e_max_dist"] < 0:
        error("The maximal distance value for the E-data has to be a real value in [0,1].", error_code=12)

    # syntactically parse the input data for the F-dataset
    if kwargs["f_data"] is not None and not os.path.exists(kwargs["f_data"]):
        error("The filepath to the F-data is invalid.", error_code=13)
    if kwargs["f_weights"] is not None and not os.path.isfile(kwargs["f_weights"]):
        error("The filepath to the weights of the F-data is invalid.", error_code=14)
    if kwargs["f_sim"] is not None and kwargs["f_sim"].lower() not in SIM_ALGOS and not os.path.isfile(kwargs["f_sim"]):
        error(
            f"The similarity metric for the F-data seems to be a file-input but the filepath is invalid.", error_code=15
        )
    if kwargs["f_dist"] is not None and kwargs["f_dist"].lower() not in DIST_ALGOS and not os.path.isfile(
            kwargs["f_dist"]):
        error(
            f"The distance metric for the F-data seems to be a file-input but the filepath is invalid.", error_code=16
        )
    if kwargs["f_sim"] is not None and kwargs["f_sim"] == "CDHIT":
        validate_cdhit_args(kwargs["f_args"])
    if kwargs["f_sim"] is not None and kwargs["f_sim"].lower() == "mmseqs":
        validate_mmseqs_args(kwargs["e_args"])
    if kwargs["f_dist"] is not None and kwargs["f_dist"] == "MASH":
        validate_mash_args(kwargs["f_args"])
    if 1 < kwargs["f_max_sim"] < 0:
        error("The maximal similarity value for the F-data has to be a real value in [0,1].", error_code=17)
    if 1 < kwargs["f_max_dist"] < 0:
        error("The maximal distance value for the F-data has to be a real value in [0,1].", error_code=18)

    return kwargs


def validate_cdhit_args(cdhit_args):
    parsed = parse_cdhit_args(cdhit_args)
    if not ((parsed["n"] == 2 and 0.4 <= parsed["c"] <= 0.5) or
            (parsed["n"] == 3 and 0.5 <= parsed["c"] <= 0.6) or
            (parsed["n"] == 4 and 0.6 <= parsed["c"] <= 0.7) or
            (parsed["n"] == 5 and 0.7 <= parsed["c"] <= 1.0)):
        error("There are restrictions on the values for n and c in CD-HIT:\n"
              "n == 5 <=> c in [0.7, 1.0]\n"
              "n == 4 <=> c in [0.6, 0.7]\n"
              "n == 3 <=> c in [0.5, 0.6]\n"
              "n == 2 <=> c in [0.4, 0.5]", error_code=19)


def validate_mash_args(mash_args):
    """
    Validate the custom arguments provided to DataSAIL for executing MASH
    Args:
        mash_args:

    Returns:

    """
    parsed = parse_mash_args(mash_args)
    if parsed["k"] < 1:
        error("MASH parameter k must be positive.", error_code=20)
    if parsed["s"] < 1:
        error("MASH parameter s must be positive.", error_code=21)


def validate_mmseqs_args(mmseqs_args):
    """
    Validate the custom arguments provided to DataSAIL for executing MMseqs.

    Args:
        mmseqs_args: String of the arguments that can be set by user
    """
    parsed = parse_mmseqs_args(mmseqs_args)
    if 1 < parsed["seq_id"] < 0:
        error("The minimum sequence identity for mmseqs has to be a value between 0 and 1.", error_code=22)


def datasail(
        techniques: List[str],
        inter=None,
        max_sec: int = 100,
        max_sol: int = 1000,
        verbose: str = "W",
        splits=None,
        names=None,
        epsilon: float = 0.05,
        solver: str = "MOSEK",
        vectorized: bool = True,
        cache: bool = False,
        cache_dir: str = None,
        e_type=None,
        e_data=None,
        e_weights=None,
        e_sim=None,
        e_dist=None,
        e_args="",
        e_max_sim: float = 1.0,
        e_max_dist: float = 1.0,
        f_type=None,
        f_data=None,
        f_weights=None,
        f_sim=None,
        f_dist=None,
        f_args="",
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
        solver: Solving algorithm to use.
        vectorized: Boolean flag indicating to use the vectorized formulation of the problems.
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
    if names is None:
        names = ["train", "val", "test"]
    if splits is None:
        splits = [0.7, 0.2, 0.1]
    kwargs = validate_args(
        output=None, techniques=techniques, inter=inter, max_sec=max_sec, max_sol=max_sol, verbosity=verbose,
        splits=splits, names=names, epsilon=epsilon, solver=solver, vectorized=not vectorized, cache=cache,
        cache_dir=cache_dir, e_type=e_type, e_data=e_data, e_weights=e_weights, e_sim=e_sim, e_dist=e_dist,
        e_args=e_args, e_max_sim=e_max_sim, e_max_dist=e_max_dist, f_type=f_type, f_data=f_data, f_weights=f_weights,
        f_sim=f_sim, f_dist=f_dist, f_args=f_args, f_max_sim=f_max_sim, f_max_dist=f_max_dist, threads=threads,
    )
    return bqp_main(**kwargs)


def sail(**kwargs) -> None:
    """
    Invocation routine of DataSAIL. Here, the arguments are validated and the main routine is invoked.

    Args:
        **kwargs: Arguments to DataSAIL in kwargs-format.
    """
    kwargs = validate_args(**kwargs)
    bqp_main(**kwargs)


if __name__ == '__main__':
    """
    Entry point for the CLI tool
    """
    sail(**parse_datasail_args(sys.argv[1:]))
