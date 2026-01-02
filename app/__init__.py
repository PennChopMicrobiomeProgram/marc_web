import os
from pathlib import Path


__version__ = "0.4.0"
__author__ = "Charlie Bushman"


def get_db_last_sync():
    if "MARC_DB_LAST_SYNC" in os.environ:
        fp = Path(os.environ["MARC_DB_LAST_SYNC"])
        if fp.exists():
            return fp.read_text().strip()

    return "Unknown"
