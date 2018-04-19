import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

DAEMON_LISTENING_PORT = 5000
ETHEREUM_JSON_RPC_ENDPOINT = ""
AGENT_CONTRACT_ADDRESS = ""
PASSTHROUGH_ENDPOINT = ""
PASSTHROUGH_ENABLED = False
BLOCKCHAIN_ENABLED = True
DB_PATH = "snetd"
LOG_LEVEL = 10
PRIVATE_KEY = ""
HDWALLET_MNEMONIC = ""
HDWALLET_INDEX = 0
POLL_SLEEP_SECS = 5
CONFIG_PATH = "snetd.config"


def init_config(config_path=None):
    if config_path is None:
        config_path = CONFIG_PATH

    try:
        # Override from file
        with open(config_path) as f:
            overrides = json.load(f)
            for k, v in overrides.items():
                logger.debug("overriding config key %s with value %s from config file", k, v)
                setattr(sys.modules[__name__], k, v)
    except:
        pass

    # Override from environment variables
    for k in dir(sys.modules[__name__]):
        if os.environ.get(k, None) is not None:
            logger.debug("overriding config key %s with value %s from environment", k, os.environ[k])
            setattr(sys.modules[__name__], k, os.environ[k])
