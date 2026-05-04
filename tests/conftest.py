"""Pytest configuration shared by all test modules.

Several test modules import ``config``/``auth``/``server`` at top level. Those
imports trigger ``config._validate_auth_config()`` which, in API-key mode
(``OAUTH_ENABLED=false``), requires ``LENSES_API_KEY`` to be non-empty.

To keep tests hermetic — independent of the developer's local ``.env`` — we
set a placeholder API key here, before any test module is collected.
``load_dotenv`` does not override existing env vars, so this also wins over
whatever sits in ``.env``.
"""

import os

os.environ.setdefault("LENSES_API_KEY", "test-key")
