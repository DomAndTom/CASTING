#!/usr/bin/env python
# coding: utf-8

# In[1]:

"""
Created on 2022-12-13 20:36:01.409428
@author: suvobanik
"""


import math
import time
from hashlib import sha256 as hashfunc

from lammps import lammps
from pymatgen.io.lammps.data import LammpsData
from pymatgen.io.xyz import XYZ

from CASTING.clusterfun import check_constrains, parm2struc, struc2param

from . import logger

# In[ ]:

cmds = ["-screen", "none", "-log", "none"]
lmp = lammps(cmdargs=cmds)
# lmp  = lammps()


class LammpsEvaluator:
    """
    Performs energy evaluations on a offspring
    """

    def __init__(self, pars):
        self.pars = pars

    def evaluate(self, structData):
        if not check_constrains(structData):
            return structData, 1e300

        struct = parm2struc(structData)
        LammpsData.from_structure(struct, atom_style="atomic").write_file(
            "in.data"
        )

        lmp.command("clear")
        lmp.command("dimension 3")
        lmp.command("box tilt large")
        lmp.command("units metal")
        lmp.command("atom_style atomic")
        lmp.command("neighbor 2.0 bin")
        lmp.command("atom_modify map array sort 0 0")
        lmp.command("boundary f f f")
        lmp.command("read_data in.data")
        lmp.command(f"{self.pars['pair_style']}")
        lmp.command(f"{self.pars['pair_coeff']}")
        lmp.command("thermo 1000")
        lmp.command("thermo_style custom step etotal atoms vol")
        lmp.command("thermo_modify format float %5.14g lost ignore")
        lmp.command("variable potential equal pe/atoms")
        lmp.command("neigh_modify one 5000 delay 0 every 1 check yes")
        lmp.command("run 0 pre no")

        # ------------guard for bad structures---------

        energy = lmp.extract_variable("potential", None, 0)

        if math.isinf(float(energy)):
            return structData, 1e300
        elif math.isnan(float(energy)):
            return structData, 1e300
        # ---------------------------------------------

        lmp.command("minimize 1.0e-8 1.0e-8 10000 10000")
        lmp.command("write_data min.geo")
        lmp.command("run 0 pre no")

        energy = lmp.extract_variable("potential", None, 0)

        # lost ignore: compare number of atoms written and expected
        expected_natom = lmp.get_natoms()
        with open("min.geo") as f:
            for i, line in enumerate(f):
                if i == 2:
                    natom = int(line.split()[0])
                    break
        if natom != expected_natom:
            return structData, 1e300

        minstruct = LammpsData.from_file(
            "min.geo", atom_style="atomic"
        ).structure

        ID = hashfunc(str(minstruct.as_dict()).encode()).hexdigest()[:6]

        minData, mineng = struc2param(
            minstruct,
            energy,
            structData['constraint'],
            CheckFrConstrains=True,
            # writefile="dumpfile.dat",
        )

        if mineng is False:
            logger.info(f'Structure {ID} failed constraints, skipped.')
            return minData, 1e300

        # output structure to xyz file
        XYZ(minstruct).write_file(f'structures/{ID}.xyz')
        open('dumpfile.dat', 'a').write(f"{time.time()} {ID} {mineng}\n")
        logger.info(f"Output structure {ID}.")

        return minData, mineng
