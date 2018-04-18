import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SERVER_PORT = 5000
ETH_NODE_ENDPOINT = "http://127.0.0.1:8545"
AGENT_CONTRACT_JSON_PATH = Path(__file__).absolute().parent.joinpath("resources", "Agent.json")
AGENT_ADDRESS = "0x781f6d9066007bbf3de18c1ba00d96a270e02c30"
SERVICE_ENDPOINT = "http://127.0.0.1:5001"
PASSTHROUGH_ENABLED = False
BLOCKCHAIN_ENABLED = True
DB_PATH = "snetd"
LOG_LEVEL = 10
HDWALLET_MNEMONIC = "orphan wheel horse track deer rotate crew heart satoshi abstract modify warrior"
HDWALLET_INDEX = 4
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
