"""Exercise the catalog transaction boundary in independent native processes."""
import os
from pathlib import Path
import subprocess
import sys

from cinema_lab.music import MusicLibrary


def test_catalog_transactions_do_not_lose_concurrent_updates(tmp_path):
    library = MusicLibrary(tmp_path)
    library.directory.mkdir(parents=True)
    library.save({"version": 1, "source_root": "source/music", "assets": {}, "counter": 0})
    worker = """
from pathlib import Path
import sys,time
from cinema_lab.music import MusicLibrary
library = MusicLibrary(Path(sys.argv[1]))
for _ in range(12):
    with library.locked():
        state = library.read()
        time.sleep(0.005)
        state['counter'] += 1
        library.save(state)
"""
    processes = [subprocess.Popen([sys.executable, "-c", worker, str(tmp_path)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8") for _ in range(2)]
    try:
        for process in processes:
            output, errors = process.communicate(timeout=30)
            assert process.returncode == 0, errors
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert library.read()["counter"] == 24
