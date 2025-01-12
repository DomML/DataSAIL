from typing import Tuple, List, Dict

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds.MurckoScaffold import MakeScaffoldGeneric
from rdkit.Chem.rdchem import MolSanitizeException

from datasail.cluster.utils import read_molecule_encoding
from datasail.reader.utils import DataSet
from datasail.settings import LOGGER


def run_ecfp(dataset: DataSet) -> Tuple[List[str], Dict[str, str], np.ndarray]:
    """
    Compute 1024Bit-ECPFs for every molecule in the dataset and then compute pairwise Tanimoto-Scores of them.

    Args:
        dataset: The dataset to compute pairwise, elementwise similarities for

    Returns:
        A tuple containing
          - the names of the clusters (cluster representatives)
          - the mapping from cluster members to the cluster names (cluster representatives)
          - the similarity matrix of the clusters (a symmetric matrix filled with 1s)
    """
    lg = RDLogger.logger()
    lg.setLevel(RDLogger.CRITICAL)
    if dataset.type != "M":
        raise ValueError("ECFP with Tanimoto-scores can only be applied to molecular data.")

    scaffolds = {}
    LOGGER.info("Start ECFP clustering")

    invalid_mols = []
    for name in dataset.names:
        scaffold = read_molecule_encoding(dataset.data[name])
        if scaffold is None:
            bo, bc = "{", "}"
            LOGGER.warning(f"RDKit cannot parse {name} {bo}{dataset.data[name]}{bc}")
            invalid_mols.append(name)
            continue
        try:
            scaffolds[name] = MakeScaffoldGeneric(scaffold)
        except MolSanitizeException:
            LOGGER.warning(f"RDKit cannot parse {name} ({dataset.data[name]})")
            invalid_mols.append(name)
            continue
    for invalid_name in invalid_mols:  # obsolete code?
        dataset.names.remove(invalid_name)
        dataset.data.pop(invalid_name)
        poppable = []
        for key, value in dataset.id_map.items():
            if value == invalid_name:
                poppable.append(key)
        for pop in poppable:
            dataset.id_map.pop(pop)

    fps = []
    cluster_names = list(set(Chem.MolToSmiles(s) for s in list(scaffolds.values())))
    for scaffold in cluster_names:
        fps.append(AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(scaffold), 2, nBits=1024))

    LOGGER.info(f"Reduced {len(dataset.names)} molecules to {len(cluster_names)}")

    LOGGER.info("Compute Tanimoto Coefficients")

    count = len(cluster_names)
    sim_matrix = np.zeros((count, count))
    for i in range(count):
        sim_matrix[i, i] = 1
        sim_matrix[i, :i] = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        sim_matrix[:i, i] = sim_matrix[i, :i]

    cluster_map = dict((name, Chem.MolToSmiles(scaffolds[name])) for name in dataset.names)
    """
    cluster_indices = dict((n, i) for i, n in enumerate(cluster_names))
    element_sim_matrix = np.ones((len(dataset.names), len(dataset.names)))
    smiles_scaff_map = dict((k, Chem.MolToSmiles(v)) for k, v in scaffolds.items())
    for i in range(len(dataset.names)):
        for j in range(i + 1, len(dataset.names)):
            element_sim_matrix[i, j] = sim_matrix[
                cluster_indices[smiles_scaff_map[dataset.names[i]]],
                cluster_indices[smiles_scaff_map[dataset.names[j]]]
            ]
            element_sim_matrix[j, i] = element_sim_matrix[i, j]
    dataset.similarity = element_sim_matrix
    """
    return cluster_names, cluster_map, sim_matrix
