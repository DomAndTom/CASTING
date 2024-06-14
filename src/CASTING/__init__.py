__all__ = [
    '__version__',
    'logger',
]

rootname = 'CASTING'
__version__ = "0.1.4"


import inspect
import sys
from pathlib import Path

rootdir = Path(inspect.getfile(__import__(rootname))).parent
swd = Path(sys.path[0])  # script directory
interactive = hasattr(sys, 'ps1')


# -------------------------------------------------------------


import logging
import logging.handlers

formatter_simple = logging.Formatter('%(levelname)s: %(message)s')
formatter_detailed = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d (%(processName)s, %(threadName)s) [%(levelname)s]: %(message)s',
    datefmt="%Y-%m-%d %Z %H:%M:%S",
)

screen = logging.StreamHandler()
screen.setFormatter(formatter_simple)
screen.setLevel(logging.NOTSET)

logfile_path = swd / f"{rootname}.log"
logfile = logging.handlers.WatchedFileHandler(logfile_path, delay=True)
logfile.setFormatter(formatter_detailed)
logfile.setLevel(logging.NOTSET + interactive * 999)

logger = logging.getLogger(rootname)
logger.setLevel(logging.INFO)  # INFO, DEBUG for -v, NOTSET for -vv
logger.addHandler(screen)
logger.addHandler(logfile)
