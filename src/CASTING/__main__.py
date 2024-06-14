import json

import typer

from . import logger, rootname


def load_inputs(filepath):
    conf = json.loads(open(filepath).read())
    logger.info(f'--- {rootname} configurations ---\n{conf}\n')
    return conf


def run(conf: dict):
    try:
        job_type = conf.get("job_type", "structure_search")
        logger.info(f'--- run {job_type} ---')
        job = __import__(f'{rootname}.run_{job_type}', fromlist=[''])
        job.run(conf)
    except ModuleNotFoundError as err:
        logger.error(f"In '{job_type}', {err}")
        raise SystemExit


def main(inputsfile: str):
    run(load_inputs(inputsfile))


if __name__ == '__main__':
    typer.run(main)
