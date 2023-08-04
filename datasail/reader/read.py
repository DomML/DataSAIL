import os
from typing import Tuple, List, Optional, Callable, Dict, Any, Generator

from datasail.reader.read_genomes import read_genome_data, remove_genome_duplicates
from datasail.reader.read_molecules import read_molecule_data, remove_molecule_duplicates
from datasail.reader.read_other import read_other_data, remove_other_duplicates
from datasail.reader.read_proteins import read_protein_data, remove_protein_duplicates
from datasail.reader.utils import read_csv, DataSet, get_prefix_args
from datasail.settings import KW_INTER, KW_E_TYPE, KW_E_DATA, KW_E_WEIGHTS, KW_E_SIM, KW_E_DIST, KW_E_MAX_SIM, \
    KW_E_MAX_DIST, KW_E_ID_MAP, KW_E_ARGS, KW_F_TYPE, KW_F_DATA, KW_F_WEIGHTS, KW_F_SIM, KW_F_DIST, KW_F_MAX_SIM, \
    KW_F_MAX_DIST, KW_F_ID_MAP, KW_F_ARGS, KW_OUTDIR, P_TYPE, M_TYPE, G_TYPE, O_TYPE


def read_data(**kwargs) -> Tuple[DataSet, DataSet, Optional[List[Tuple[str, str]]], Optional[List[Tuple[str, str]]]]:
    """
    Read data from the input arguments.

    Args:
        **kwargs: Arguments from commandline

    Returns:
        Two datasets storing the information on the input entities and a list of interactions between
    """
    # TODO: Semantic checks of arguments
    match kwargs[KW_INTER]:
        case None:
            old_inter = None
        case x if isinstance(x, str):
            old_inter = list(tuple(x) for x in read_csv(kwargs[KW_INTER]))
        case x if isinstance(x, list):
            old_inter = kwargs[KW_INTER]
        case x if isinstance(x, Callable):
            old_inter = kwargs[KW_INTER]()
        case x if isinstance(x, Generator):
            old_inter = list(kwargs[KW_INTER])
        case _:
            raise ValueError()

    e_dataset, inter = read_data_type(kwargs[KW_E_TYPE])(
        kwargs[KW_E_DATA], kwargs[KW_E_WEIGHTS], kwargs[KW_E_SIM], kwargs[KW_E_DIST], kwargs[KW_E_MAX_SIM],
        kwargs[KW_E_MAX_DIST], kwargs.get(KW_E_ID_MAP, None), old_inter, 0
    )
    e_dataset.args = kwargs[KW_E_ARGS]
    f_dataset, inter = read_data_type(kwargs[KW_F_TYPE])(
        kwargs[KW_F_DATA], kwargs[KW_F_WEIGHTS], kwargs[KW_F_SIM], kwargs[KW_F_DIST], kwargs[KW_F_MAX_SIM],
        kwargs[KW_F_MAX_DIST], kwargs.get(KW_F_ID_MAP, None), inter, 1
    )
    f_dataset.args = kwargs[KW_F_ARGS]

    return e_dataset, f_dataset, inter, old_inter


def check_duplicates(**kwargs) -> Dict[str, Any]:
    """
    Remove duplicates from the input data. This is done for every input type individually by calling the respective
    function here.

    Args:
        **kwargs: Keyword arguments provided to the program

    Returns:
        The updated keyword arguments as data might have been moved
    """
    os.makedirs(os.path.join(kwargs.get(KW_OUTDIR, None) or "", "tmp"), exist_ok=True)

    # remove duplicates from first dataset
    kwargs.update(
        get_remover_fun(kwargs[KW_E_TYPE])("e_", kwargs.get(KW_OUTDIR, None) or "", **get_prefix_args("e_", **kwargs))
    )

    # if existent, remove duplicates from second dataset as well
    if kwargs[KW_F_TYPE] is not None:
        kwargs.update(
            get_remover_fun(kwargs[KW_F_TYPE])("f_", kwargs.get(KW_OUTDIR, None) or "",
                                               **get_prefix_args("f_", **kwargs))
        )

    return kwargs


def get_remover_fun(data_type: str) -> Callable:
    """
    Proxy function selecting the correct function to remove duplicates from the input data by matching the input
    data-type.

    Args:
        data_type: Input data-type

    Returns:
        A callable function to remove duplicates from an input dataset
    """
    match data_type:
        case "P":
            return remove_protein_duplicates
        case "M":
            return remove_molecule_duplicates
        case "G":
            return remove_genome_duplicates
        case _:
            return remove_other_duplicates


def read_data_type(data_type: chr) -> Callable:
    """
    Convert single-letter representation of the type of data to handle to the full name.

    Args:
        data_type: Single letter representation of the type of data

    Returns:
        full name of the type of data
    """
    match data_type:
        case "P":
            return read_protein_data
        case "M":
            return read_molecule_data
        case "G":
            return read_genome_data
        case "O":
            return read_other_data
        case _:
            return read_none_data


def read_none_data(*_) -> Tuple[DataSet, Optional[List[Tuple[str, str]]]]:
    """
    Dummy method to account for unknown data type

    Returns:
        An empty dataset according to a type of input data that cannot be read
    """
    return DataSet(), _[-2]
