"""Backend package.

Load environment variables from ``Backend/.env`` as early as possible.

The app is started from the project root (e.g. ``uvicorn Backend.main:app``)
so a bare ``load_dotenv()`` — which searches the current working directory —
would never find ``Backend/.env``. Loading it here, from a path relative to
this file, guarantees the keys are present before any submodule runs its
module-level model initialization.
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))
