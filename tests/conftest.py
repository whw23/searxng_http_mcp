"""Global test configuration."""

import os

PROXY_VARS = ("http_proxy", "https_proxy", "all_proxy",
              "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")

for var in PROXY_VARS:
    os.environ.pop(var, None)
