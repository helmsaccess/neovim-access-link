"""Keep the test sources separate from the local VM and its run artifacts."""

import os
from pathlib import Path


SOURCES = Path(__file__).resolve().parent
DEFAULT_WORKSPACE = SOURCES.parents[3] / "nal-aux" / "tools" / "windows-focus-vm"
WORKSPACE = Path(os.environ.get("NAL_TEST_WORK_DIR", DEFAULT_WORKSPACE)).resolve()
if WORKSPACE.exists() and not WORKSPACE.is_dir():
    raise NotADirectoryError(WORKSPACE)
