import argparse
import logging
import os.path

from datasail.run import bqp_main

verb_map = {
    "C": logging.CRITICAL,
    "F": logging.FATAL,
    "E": logging.ERROR,
    "W": logging.WARNING,
    "I": logging.INFO,
    "D": logging.DEBUG,
}


def parse_args():
    parser = argparse.ArgumentParser(
        prog="DataSAIL - Data Splitting Against Information Leaking",
        description="Data SAIL is a tool proving you with sophisticated splits of any type of data to challenge your "
                    "AI model. DataSAIL is able to compute several different splits of data preventing information "
                    "from leaking from the training set into the validation or test sets.",
    )
    parser.add_argument(
        "-i",
        "--inter",
        type=str,
        default=None,
        dest="inter",
        help="Path to TSV file of protein-ligand interactions."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        dest="output",
        help="Output directory to store the splits in.",
    )
    parser.add_argument(
        "--to-sec",
        default=10,
        dest="max_sec",
        type=int,
        help="Maximal time to spend optimizing the objective in seconds. This does not include preparatory work such "
             "as parsing data and cluster the input."
    )
    parser.add_argument(
        "--to-sol",
        default=1000,
        dest="max_sol",
        type=int,
        help="Maximal number of solutions to compute until end of search (in case no optimum was found)."
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        default="W",
        type=str,
        choices=["C", "F", "E", "W", "I", "D"],
        dest='verbosity',
        help="Verbosity level of the program. Choices are: [C]ritical, [F]atal, [E]rror, [W]arning, [I]nfo, [D]ebug",
    )
    split = parser.add_argument_group("Splitting Arguments")
    split.add_argument(
        "-t",
        "--technique",
        type=str,
        choices=["R", "ICS", "ICD", "CCS", "CCD"],
        default="R",
        dest="technique",
        help="Select the mode to split the data. R: random split, ICS: identity-based cold-single split, "
             "ICD: identity-based cold-double split, CCS: similarity-based cold-protein split, "
             "CCD: similarity-based cold-drug split"
    )
    split.add_argument(
        "-s",
        "--splits",
        default=[0.7, 0.2, 0.1],
        nargs="+",
        type=float,
        dest="splits",
        help="Sizes of the individual splits the program shall produce.",
    )
    split.add_argument(
        "--names",
        default=None,
        dest="names",
        nargs="+",
        type=str,
        help="Names of the splits in order of the -s argument."
    )
    split.add_argument(
        "--limit",
        default=0.05,
        type=float,
        dest="limit",
        help="Multiplicative factor by how much the limits of the splits can be exceeded.",
    )
    prot = parser.add_argument_group("First Input Arguments")
    prot.add_argument(
        "--e-type",
        type=str,
        dest="e_type",
        choices=["P", "M", "G", "O"],
        default=None,
        help="Type of the first data batch to the program. Choices are: [P]rotein, [M]olecule, [G]enome, [O]ther",
    )
    prot.add_argument(
        "--e-data",
        type=str,
        dest="e_data",
        default=None,
        help="First input to the program. This can either be the filepath a directory containing only data files.",
    )
    prot.add_argument(
        "--e-weights",
        type=str,
        dest="e_weights",
        default=None,
        help="Custom weights of the first bunch of samples. The file has to have TSV format where every line is of the "
             "form [id >tab< weight]. The prot_id has to match a protein id from the protein input argument.",
    )
    prot.add_argument(
        "--e-sim",
        type=str,
        dest="e_sim",
        default=None,
        help="Provide the name of a method to determine similarity between samples of the first input dataset. This "
             "can either be >WLK<, >mmseqs<, or a filepath to a file storing the pairwise similarities in TSV.",
    )
    prot.add_argument(
        "--e-dist",
        type=str,
        dest="e_dist",
        default=None,
        help="Provide the name of a method to determine distance between samples of the first input data. This can be "
             ">MASH< or a filepath to a file storing the pairwise distances in TSV."
    )
    prot.add_argument(
        "--e-max-sim",
        type=float,
        dest="e_max_sim",
        default=1.0,
        help="Maximum similarity of two samples from the first data in two split."
    )
    prot.add_argument(
        "--e-max-dist",
        type=float,
        dest="e_max_dist",
        default=1.0,
        help="Maximal distance of two samples from the second data in the same split."
    )
    prot = parser.add_argument_group("Second Input Arguments")
    prot.add_argument(
        "--f-type",
        type=str,
        dest="f_type",
        default=None,
        help="Type of the second data batch to the program.",
    )
    prot.add_argument(
        "--f-data",
        type=str,
        dest="f_data",
        default=None,
        help="Second input to the program. This can either be the filepath a directory containing only data files.",
    )
    prot.add_argument(
        "--f-weights",
        type=str,
        dest="f_weights",
        default=None,
        help="Custom weights of the second bunch of samples. The file has to have TSV format where every line is of "
             "the form [prot_id >tab< weight]. The prot_id has to match a protein id from the protein input argument.",
    )
    prot.add_argument(
        "--f-sim",
        type=str,
        dest="e_sim",
        default=None,
        help="Provide the name of a method to determine similarity between samples of the second input dataset. This "
             "can either be >WLK<, >mmseqs<, or a filepath to a file storing the pairwise similarities in TSV.",
    )
    prot.add_argument(
        "--f-dist",
        type=str,
        dest="f_dist",
        default=None,
        help="Provide the name of a method to determine distance between samples of the second input dataset. This can "
             "be >MASH< or a filepath to a file storing the pairwise distances in TSV."
    )
    prot.add_argument(
        "--f-max-sim",
        type=float,
        dest="f_max_sim",
        default=1.0,
        help="Maximum similarity of two samples from the second dataset in two split."
    )
    prot.add_argument(
        "--f-max-dist",
        type=float,
        dest="f_max_dist",
        default=1.0,
        help="Maximal distance of two samples from the second dataset in the same split."
    )
    return vars(parser.parse_args())


def error(msg, code):
    logging.error(msg)
    exit(code)


def validate_args(**kwargs):
    logging.basicConfig(level=verb_map[kwargs["verbosity"]])
    logging.info("Validating arguments")

    if not os.path.isdir(kwargs["output"]):
        logging.warning("Output directory does not exist, DataSAIL creates it automatically")
        os.makedirs(kwargs["output"], exist_ok=True)

    if len(kwargs["splits"]) < 2:
        error("Less then two splits required. This is no useful input, please check the input again.", 1)
    if kwargs["names"] is None:
        kwargs["names"] = [f"Split{x:03s}" for x in range(len(kwargs["splits"]))]
    elif len(kwargs["names"]) != len(kwargs["names"]):
        error("Different number of splits and names. You have to give the same number of splits and names for them.", 2)
    kwargs["splits"] = [x/sum(kwargs["splits"]) for x in kwargs["splits"]]

    return kwargs


def sail(**kwargs):
    kwargs = validate_args(**kwargs)
    bqp_main(**kwargs)


if __name__ == '__main__':
    sail(**parse_args())