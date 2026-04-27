import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")
ALGO_LOG_FILE = os.path.join(LOG_DIR, "main_algo.log")


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _setup_algo_logger()


def _setup_algo_logger():
    """
    Dedicated logger for the RAG pipeline trace.

    Writes to ``backend/logs/main_algo.log`` with a cleaner format
    focused on readability — no module names, just timestamps and
    the decision trace.
    """
    algo = logging.getLogger("algo")
    algo.setLevel(logging.DEBUG)
    algo.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(ALGO_LOG_FILE)
    fh.setFormatter(fmt)
    algo.addHandler(fh)
