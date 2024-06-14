import random

import numpy as np

import CASTING
from CASTING.clusterfun import createRandomData
from CASTING.perturb import perturbate
import CASTING.optimizers as optimizers

logger = CASTING.logger

simulator_list = {
    # name: (module, class name)
    'lammps': ('CASTING.lammpsEvaluate', 'LammpsEvaluator'),
}


def run(conf):
    seed = 12
    random.seed(seed)
    np.random.seed(seed)

    # initialize root node data
    logger.info('Create random initial structure.')
    L = conf.get('lattice', None)
    C = conf.get('constraint', None)
    root_node = createRandomData(L, C, multiplier=10)

    # initialize evaluator
    try:
        simname = conf.get('simulator', 'unspecified')
        simpars = conf.get(simname, {})
        modulename, clsname = simulator_list[simname]
        sim_module = __import__(f'{modulename}', fromlist=[''])
        evaluator = getattr(sim_module, clsname)(**simpars)
        logger.info(f'Initialized {simname} simulator.')
    except Exception as err:
        print(f"Cannot load '{simname}' simulator. {err}")
        raise SystemExit

    # run optimizer
    pt = {
        'max_mutation': 0.05,  # Put in fraction of the box length 0.01 means 100*0.01 =1Angs
    }
    optname = conf['optimizer']['name']
    optimizer = getattr(optimizers, optname)
    logger.info(f'Initialized {optname} optimizer.')
    optimizer(
        root_node,
        perturbate(**pt).perturb,  # perturbation
        evaluator.evaluate,
        niterations=2000,
        headexpand=10,
        nexpand=3,
        nsimulate=3,
        nplayouts=10,
        exploreconstant=1,
        maxdepth=12,
        a=0,
        selected_node=0,
    )
