"""
Created on 2022-12-13 20:36:01.409428
@author: suvobanik
"""

from collections import Counter
from itertools import product
from random import choice, random, shuffle

import networkx as nx
import numpy as np
from ase.build import bulk, make_supercell
from pymatgen.core import Structure
from scipy.spatial.distance import pdist, squareform

from CASTING.utilis import DistanceMatrix, get_factors, get_lattice

from . import logger


def random_sub_cluster_sample(A, natoms):
    indexes = np.arange(0, natoms, 1)
    sampled_nodes = [choice(indexes)]
    for i in range(natoms - 1):
        connections = np.where(A[sampled_nodes[i], :] != 0)[0]
        connections_wth_sam = [
            n for n in connections if n not in sampled_nodes
        ]
        shuffle(connections_wth_sam)
        next_node = connections_wth_sam[0]
        sampled_nodes.append(next_node)

    return sampled_nodes


def createRandomData(lattice, constrains, multiplier=10):
    L = lattice
    C = constrains

    natoms = np.random.randint(C["min_num_atoms"], C["max_num_atoms"])

    # --------Species list creation -----------

    norm = sum(list(C["composition"].values()))

    species = [
        element
        for k, v in C["composition"].items()
        for element in [k] * int(natoms * v / norm)
    ]

    shuffle(species)

    # ----------------Bulk FCC with natoms X multiplier atoms and select cluster with random walk -----------

    r0 = C["min_atom_pair_distance"]
    r1 = C["max_atom_pair_distance"]
    # radius of an indivisual atom from fcc packing
    r = (r1 + random() * abs(r0 - r1)) * 0.5
    a = 2 * 2**0.5 * r
    a1 = bulk("Cu", "fcc", a=a)  # 'Cu' dummy species
    factors = get_factors(natoms * multiplier, 3)
    P = np.diag(factors, k=0)  # transformation mattrx
    pos = make_supercell(a1, P).get_positions()
    A = squareform(pdist(pos, metric="euclidean"))
    A[A > 2 * r] = 0
    A[A != 0] = 1
    while True:
        try:
            sampled_nodes = random_sub_cluster_sample(A, natoms)
            break
        except Exception:
            continue

    latt = get_lattice(
        **{
            **{
                k: np.random.uniform(L[f'min_{k}'], L[f'max_{k}'])
                + 2.0 * L[f'pad_{k}']
                for k in ['a', 'b', 'c']
            },
            **{
                k: np.random.uniform(L[f'min_{k}'], L[f'max_{k}'])
                for k in ['alpha', 'beta', 'gamma']
            },
        }
    )

    M = latt.matrix  # lattice matrix

    cluster_pos = pos[sampled_nodes, :]
    box_centre = np.sum(M, axis=0) * 0.5
    cluster_centre = np.mean(cluster_pos, axis=0)
    cluster_pos = box_centre + cluster_centre - cluster_pos
    cluster_pos_fractional = np.matmul(cluster_pos, np.linalg.inv(M))

    return {
        "lattice": latt,
        "parameters": cluster_pos_fractional.flatten(),
        "species": species,
        "constraint": C,
    }


def get_coords(parameters):
    coords = parameters
    coords = coords.reshape(int(coords.shape[0] / 3), 3)
    return coords


def check_constrains(structData):
    parameters = structData["parameters"].copy()
    species = structData["species"].copy()
    specieCount = dict(Counter(species))
    coords = get_coords(parameters)

    constrains = structData['constraint']

    # ======= number of atom constrains==============

    natoms = coords.shape[0]
    if (
        not constrains['min_num_atoms']
        <= natoms
        <= constrains['max_num_atoms']
    ):
        logger.debug("# of atoms inconsistent.")
        return False

    # ============ composition check=================

    composition = constrains["composition"]

    if list(composition.keys()).sort() != list(specieCount.keys()).sort():
        logger.debug("composition inconsistent.")
        return False

    for key in composition.keys():
        if specieCount[key] % composition[key] != 0:
            logger.debug("composition inconsistent.")
            return False

    # ======================================

    latt = structData["lattice"]
    M = np.array((latt.matrix))
    D = DistanceMatrix(coords, M)
    np.fill_diagonal(D, 1e300)
    A = np.empty(D.shape)

    indices = {}

    for key in constrains["composition"].keys():
        indices[key] = np.where(np.array(species) == key)[0].tolist()

    for c in product(list(indices.keys()), repeat=2):
        index1, index2 = indices[c[0]], indices[c[1]]
        d_sub = D[index1, :][:, index2]

        rmin = constrains["min_atom_pair_distance"]
        rmax = constrains["max_atom_pair_distance"]
        if np.sum(d_sub < rmin):  # overlapping test
            logger.debug("overlapping atoms.")
            return False

        d_sub[d_sub <= rmax] = 1
        d_sub[d_sub > rmax] = 0

        C = A[index1, :]
        C[:, index2] = d_sub
        A[index1, :] = C

    G = nx.from_numpy_matrix(A)

    # -------fragmentation test----------------

    if len(list(nx.connected_components(G))) > 1:
        logger.debug("Fragmented cluster.")
        return False

    return True


# ---------------------------------------


def parm2struc(structData):
    parameters = structData["parameters"].copy()
    return Structure(
        structData["lattice"],
        structData["species"].copy(),
        get_coords(parameters),
        to_unit_cell=True,
    )


# ----------------------------------------


def struc2param(
    struct, energy, constrains, CheckFrConstrains=False, writefile=None
):
    lattice = getattr(struct, "lattice")

    pos = np.array([list(site.frac_coords) for site in struct.sites]).flatten()

    species = [site.specie.symbol for site in struct.sites]

    # latt = [
    #     lattice.a,
    #     lattice.b,
    #     lattice.c,
    #     lattice.alpha,
    #     lattice.beta,
    #     lattice.gamma,
    # ]

    StructData = {
        "lattice": lattice,
        "parameters": pos,
        "species": species,
        "constraint": constrains,
    }

    if CheckFrConstrains and not check_constrains(StructData):
        return StructData, False

    # if writefile is not None:
    #     dataString = (
    #         " ".join(map(str, latt + pos.tolist()))
    #         + "|"
    #         + " ".join(species)
    #         + "|"
    #         + "{}".format(energy)
    #     )

    #     with open(writefile, "a") as outfile:
    #         outfile.write("{}\n".format(dataString))

    return StructData, energy
