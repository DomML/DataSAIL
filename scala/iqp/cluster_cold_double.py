import logging
from typing import List, Optional, Tuple, Dict

import cvxpy


def solve_cc_iqp_cvxpy(
        drug_clusters: List[object],
        drug_weights: List[float],
        drug_similarities: List[List[float]],
        drug_threshold: float,
        prot_clusters: List[object],
        prot_weights: List[float],
        prot_similarities: List[List[float]],
        prot_threshold: float,
        inter: List[List[int]],
        limit: float,
        splits: List[float],
        names: List[str],
        max_sec: int,
        max_sol: int,
) -> Optional[Tuple[List[Tuple[str, str, str]], Dict[str, str], Dict[str, str]]]:
    alpha = 0.1
    inter_count = sum(sum(row) for row in inter)

    x_d = {}
    for b in range(len(splits)):
        for i in range(len(drug_clusters)):
            x_d[i, b] = cvxpy.Variable(boolean=True)
    x_p = {}
    for b in range(len(splits)):
        for j in range(len(prot_clusters)):
            x_p[j, b] = cvxpy.Variable(boolean=True)
    x_e = {}
    for b in range(len(splits)):
        for i, drug in enumerate(drug_clusters):
            for j, protein in enumerate(prot_clusters):
                x_e[i, j, b] = cvxpy.Variable(boolean=True)

    constraints = []

    for i in range(len(drug_clusters)):
        constraints.append(sum(x_d[i, b] for b in range(len(splits))) == 1)
    for j in range(len(prot_clusters)):
        constraints.append(sum(x_p[j, b] for b in range(len(splits))) == 1)
    for i in range(len(drug_clusters)):
        for j in range(len(prot_clusters)):
            constraints.append(sum(x_e[i, j, b] for b in range(len(splits))) <= 1)

    for b in range(len(splits)):
        var = sum(
            x_e[i, j, b] * inter[i][j] for i in range(len(drug_clusters)) for j in range(len(prot_clusters))
        )
        constraints.append(int(splits[b] * inter_count * (1 - limit)) <= var)
        constraints.append(var <= int(splits[b] * inter_count * (1 + limit)))

        for i in range(len(drug_clusters)):
            for j in range(len(prot_clusters)):
                constraints.append(x_e[i, j, b] >= (x_d[i, b] + x_p[j, b] - 1.5))
                constraints.append(x_e[i, j, b] <= (x_d[i, b] + x_p[j, b]) * 0.5)
                constraints.append(x_d[i, b] >= x_e[i, j, b])
                constraints.append(x_p[j, b] >= x_e[i, j, b])

        for i in range(len(drug_clusters)):
            for j in range(i + 1, len(drug_clusters)):
                constraints.append((x_d[i, b] - x_d[j, b]) ** 2 * drug_similarities[i][j] <= drug_threshold)

        for i in range(len(prot_clusters)):
            for j in range(i + 1, len(prot_clusters)):
                constraints.append((x_p[i, b] - x_p[j, b]) ** 2 * prot_similarities[i][j] <= prot_threshold)

    inter_loss = sum(
        alpha * sum(
            (1 - x_e[i, j, b]) * inter[i][j] for i in range(len(drug_clusters)) for j in range(len(prot_clusters))
        ) + sum(
            (x_d[i, b] - x_d[j, b]) ** 2 * drug_similarities[i][j] for i in range(len(drug_clusters))
            for j in range(i + 1, len(drug_clusters))
        ) + sum(
            (x_p[i, b] - x_p[j, b]) ** 2 * prot_similarities[i][j] for i in range(len(prot_clusters))
            for j in range(i + 1, len(prot_clusters))
        ) for b in range(len(splits))
    )

    objective = cvxpy.Minimize(inter_loss)
    problem = cvxpy.Problem(objective, constraints)
    problem.solve(solver=cvxpy.MOSEK, qcp=True)

    # report the found solution
    output = ([], {}, {})
    if problem.status == "optimal":
        for i, drug in enumerate(drug_clusters):
            for b in range(len(splits)):
                if x_d[i, b].value > 0:
                    output[1][drug_clusters[i]] = names[b]
        for j, protein in enumerate(prot_clusters):
            for b in range(len(splits)):
                if x_p[j, b].value > 0:
                    output[2][prot_clusters[j]] = names[b]
        for i, drug in enumerate(drug_clusters):
            for j, protein in enumerate(prot_clusters):
                for b in range(len(splits)):
                    if x_e[i, j, b].value > 0:
                        output[0].append((drug_clusters[i], prot_clusters[j], names[b]))
                if sum(x_e[i, j, b].value for b in range(len(splits))) == 0:
                    output[0].append((drug_clusters[i], prot_clusters[j], "not selected"))
        return output
    else:
        logging.warning(
            'MOSEK cannot solve the problem. Please consider relaxing split restrictions, '
            'e.g., less splits, or a higher tolerance level for exceeding cluster limits.'
        )
    return None


if __name__ == '__main__':
    solve_cc_iqp_cvxpy(
        ["D1", "D2", "D3"],
        [],
        [
            [5, 5, 0],
            [5, 5, 0],
            [0, 0, 5],
        ],
        4,
        ["P1", "P2", "P3"],
        [],
        [
            [5, 5, 0],
            [5, 5, 0],
            [0, 0, 5],
        ],
        4,
        [
            [9, 9, 0],
            [9, 9, 0],
            [0, 0, 9],
        ],
        0.2,
        [0.8, 0.2],
        ["train", "test"],
        0,
        0,
    )
