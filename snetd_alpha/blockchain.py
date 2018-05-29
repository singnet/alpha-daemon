import asyncio
import hashlib
import json
import logging
from pathlib import Path

import bip32utils
import ecdsa
from mnemonic import Mnemonic
from web3 import Web3, WebsocketProvider, HTTPProvider

from snetd_alpha import configuration as config

logger = logging.getLogger(__name__)


class BlockchainClient:
    def __init__(self, app):
        self.app = app

        # Configure web3
        if config.ETHEREUM_JSON_RPC_ENDPOINT.startswith("ws:"):
            provider = WebsocketProvider(config.ETHEREUM_JSON_RPC_ENDPOINT)
        else:
            provider = HTTPProvider(config.ETHEREUM_JSON_RPC_ENDPOINT)
        self.w3 = Web3(provider)
        self.w3.eth.enable_unaudited_features()  # Pending security audit, but required for offline signing of txns

        # Setup agent contract
        with open(Path(__file__).absolute().parent.joinpath("resources", "Agent.json")) as f:
            abi = json.load(f)["abi"]
            self.agent = self.w3.eth.contract(address=self.to_checksum_address(config.AGENT_CONTRACT_ADDRESS), abi=abi)

        if config.PRIVATE_KEY and config.PRIVATE_KEY != "":
            if config.PRIVATE_KEY.startswith("0x"):
                self.private_key = bytes(bytearray.fromhex(config.PRIVATE_KEY[2:]))
            else:
                self.private_key = bytes(bytearray.fromhex(config.PRIVATE_KEY))
        else:
            # Derive key
            master_key = bip32utils.BIP32Key.fromEntropy(Mnemonic("english").to_seed(config.HDWALLET_MNEMONIC))
            purpose_subtree = master_key.ChildKey(44 + bip32utils.BIP32_HARDEN)
            coin_type_subtree = purpose_subtree.ChildKey(60 + bip32utils.BIP32_HARDEN)
            account_subtree = coin_type_subtree.ChildKey(bip32utils.BIP32_HARDEN)
            change_subtree = account_subtree.ChildKey(0)
            account = change_subtree.ChildKey(config.HDWALLET_INDEX)
            self.private_key = account.PrivateKey()

        public_key = ecdsa.SigningKey.from_string(string=self.private_key,
                                                  curve=ecdsa.SECP256k1,
                                                  hashfunc=hashlib.sha256).get_verifying_key()
        self.address = self.to_checksum_address("0x" + self.w3.sha3(hexstr=public_key.to_string().hex())[12:].hex())

    def to_checksum_address(self, address):
        if self.w3.isChecksumAddress(address):
            return address
        return self.w3.toChecksumAddress(address)

    async def validate_job_invocation(self, job_address, job_signature):
        job_address = self.to_checksum_address(job_address)
        logger.debug("validating job invocation; job_address: %s; job_signature: %s", job_address, job_signature)

        db_entry = self.app["db"].get(job_address, {})

        # Quick rejection for locally completed jobs
        if db_entry.get("completed", False):
            logger.error("job already completed; job_address: %s", job_address)
            return False

        v, r, s = self.parse_job_signature(job_signature)

        # Quick validation for jobs we know are funded and haven't been completed locally
        h = self.w3.soliditySha3(['string', 'bytes32'],
                                 ["\x19Ethereum Signed Message:\n32", self.w3.sha3(hexstr=job_address)])
        if (db_entry.get("state", "") == "FUNDED" and
                self.w3.eth.account.recoverHash(h, (v, r, s)) == db_entry.get("consumer", "")):
            logger.debug("validated job locally; job_address: %s", job_address)
            return True

        # Validate on chain otherwise
        logger.debug("failed to validate job locally, reverting to Agent.validateJobInvocation.call; job_address: %s",
                     job_address)
        return self.agent.functions.validateJobInvocation(job_address, v, r, s).call()

    async def complete_job(self, job_address, job_signature):
        job_address = self.to_checksum_address(job_address)
        logger.debug("completing job; job_address: %s", job_address)

        try:
            v, r, s = self.parse_job_signature(job_signature)
            nonce = self.w3.eth.getTransactionCount(self.address)
            txn = self.agent.functions.completeJob(job_address, v, r, s).buildTransaction({
                "from": self.address,
                "nonce": nonce,
                "gas": 1000000
            })
            signed_txn = self.w3.eth.account.signTransaction(txn, self.private_key)
            txn_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

            # Wait for transaction to be mined
            while self.w3.eth.getTransactionReceipt(txn_hash) is None:
                await asyncio.sleep(config.POLL_SLEEP_SECS)

        except Exception as e:
            logger.error("encountered error while completing job; error: %s", e)

    async def process_events(self):
        db = self.app["db"]

        try:
            db["last_block"] = last_block = db.get("last_block", self.w3.eth.getBlock("latest")["number"])

        except Exception as e:
            logger.error("encountered error while determining last block, defaulting to 0; error: %s", e)
            db["last_block"] = last_block = 0

        job_created = self.agent.events.JobCreated()
        job_funded = self.agent.events.JobFunded()
        job_completed = self.agent.events.JobCompleted()

        while True:
            try:
                current_block = self.w3.eth.getBlock("latest")["number"]
                if last_block != current_block:
                    for i in range(last_block + 1, current_block + 1):
                        block = self.w3.eth.getBlock(i)
                        for txn_hash in block["transactions"]:
                            txn_receipt = self.w3.eth.getTransactionReceipt(txn_hash)
                            if len(txn_receipt["logs"]) > 0:

                                for event in (e for e in job_created.processReceipt(txn_receipt) if
                                              e["address"] == self.agent.address):
                                    job_address = event["args"]["job"]
                                    db_entry = db.get(job_address, {})
                                    db_entry["state"] = "PENDING"
                                    db_entry["consumer"] = event["args"]["consumer"]
                                    db[job_address] = db_entry
                                    logger.debug("received JobCreated event; job_address: %s; db entry: %s",
                                                 job_address, db_entry)

                                for event in (e for e in job_funded.processReceipt(txn_receipt) if
                                              e["address"] == self.agent.address):
                                    job_address = event["args"]["job"]
                                    db_entry = db.get(job_address, {})
                                    db_entry["state"] = "FUNDED"
                                    db[job_address] = db_entry
                                    logger.debug("received JobFunded event; job_address: %s; db entry: %s",
                                                 job_address, db_entry)

                                for event in (e for e in job_completed.processReceipt(txn_receipt) if
                                              e["address"] == self.agent.address):
                                    job_address = event["args"]["job"]
                                    logger.debug("received JobCompleted event, deleting db entry; job_address: %s",
                                                 job_address)
                                    del db[job_address]

                    db["last_block"] = last_block = current_block

            except Exception as e:
                logger.error("encountered error while processing events; error: %s", e)

            await asyncio.sleep(config.POLL_SLEEP_SECS)

    def parse_job_signature(self, job_signature):
        if job_signature.startswith("0x"):
            job_signature = job_signature[2:]
        v = self.w3.toInt(hexstr=job_signature[128:130])
        if v < 27:
            v += 27
        r = self.w3.toBytes(hexstr=job_signature[0:64])
        s = self.w3.toBytes(hexstr=job_signature[64:128])
        return v, r, s
