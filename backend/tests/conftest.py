"""Tests run fully offline: no AMD model calls, no Evolus calls, no quota or credits spent.
Set before any app import; python-dotenv does not override variables that already exist."""
import os

for _k in ("AMD_TF_API_KEY", "AMD_TF_BASE_URL", "EVOLUS_API_KEY", "EVOLUS_APP_ID", "EVOLUS_AGENT_ID"):
    os.environ[_k] = ""
os.environ["DEMO_MODE"] = "1"
