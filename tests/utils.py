import os
import shutil


def read_tsv(filepath):
    assert os.path.exists(filepath)
    with open(filepath, "r") as d:
        mols = [line.strip().split("\t") for line in d.readlines()]
    os.remove(filepath)
    return mols


def check_folder(output_root, epsilon, prot_weight, drug_weight):
    prot_map, drug_map = None, None
    if prot_weight is not None:
        with open(prot_weight, "r") as in_data:
            prot_map = dict((k, float(v)) for k, v in [tuple(line.strip().split("\t")[:2]) for line in in_data.readlines()])
    if drug_weight is not None:
        with open(drug_weight, "r") as in_data:
            drug_map = dict((k, float(v)) for k, v in [tuple(line.strip().split("\t")[:2]) for line in in_data.readlines()])

    split_data = []
    if os.path.exists(os.path.join(output_root, "inter.tsv")):
        split_data.append(("I", read_tsv(os.path.join(output_root, "inter.tsv"))))
    if os.path.exists(os.path.join(output_root, "Protein_1.tsv")):
        split_data.append(("P", read_tsv(os.path.join(output_root, "Protein_1.tsv"))))
    if os.path.exists(os.path.join(output_root, "Protein_2.tsv")):
        split_data.append(("P", read_tsv(os.path.join(output_root, "Protein_2.tsv"))))
    if os.path.exists(os.path.join(output_root, "Molecule_1.tsv")):
        split_data.append(("D", read_tsv(os.path.join(output_root, "Molecule_1.tsv"))))
    if os.path.exists(os.path.join(output_root, "Molecule_2.tsv")):
        split_data.append(("D", read_tsv(os.path.join(output_root, "Molecule_2.tsv"))))

    assert len(split_data) > 0

    for n, data in split_data:
        # with open("../tests/data/pipeline/prot_sim.tsv", "r") as d:
        #     listing = [line.strip().split("\t")[0] for line in d.readlines()[1:]]
        # print("\n".join(str(x) for x in sorted(data, key=lambda x: listing.index(x[0]))))
        splits = list(zip(*data))
        if n == "P" and prot_map is not None:
            trains = sum(prot_map[p] for p, s in data if s == "train")
            tests = sum(prot_map[p] for p, s in data if s == "test")
        elif n == "D" and drug_map is not None:
            trains = sum(drug_map[d] for d, s in data if s == "train")
            tests = sum(drug_map[d] for d, s in data if s == "test")
        else:
            trains, tests = splits[-1].count("train"), splits[-1].count("test")
        train_frac, test_frac = trains / (trains + tests), tests / (trains + tests)
        assert 0.7 * (1 - epsilon) <= train_frac <= 0.7 * (1 + epsilon)
        assert 0.3 * (1 - epsilon) <= test_frac <= 0.3 * (1 + epsilon)
        if n == "I":
            break

    # shutil.rmtree(output_root)
