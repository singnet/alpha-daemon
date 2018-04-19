import logging
import shelve

import aiohttp_cors
import jsonrpcclient
from aiohttp import web
from jsonrpcserver.aio import methods
from jsonrpcserver.exceptions import InvalidParams, ServerError

from snetd_alpha import configuration as config
from snetd_alpha.blockchain import BlockchainClient

logger = logging.getLogger(__name__)


class HandlerCreator(dict):
    def __init__(self, d):
        super(HandlerCreator, self).__init__()
        self.d = d

    def __missing__(self, key):
        methods.add(self.d.create_passthrough(key), key)
        return self[key]


class PassthroughClient:
    def __init__(self):
        self.enabled = config.PASSTHROUGH_ENABLED

    def request(self, endpoint, method, **kwargs):
        if self.enabled:
            return jsonrpcclient.request(endpoint, method, **kwargs)
        else:
            return {"method": method, **kwargs}


class SingularityNetDaemon:
    def __init__(self):
        self.app = web.Application()
        self.chain = BlockchainClient(self.app)
        methods._items = HandlerCreator(self)

        if config.BLOCKCHAIN_ENABLED:
            self.app.on_startup.append(self.setup_db)
            self.app.on_startup.append(self.process_completions)
            self.app.on_startup.append(self.create_event_task)
            self.app.on_cleanup.append(self.cancel_event_task)
            self.app.on_cleanup.append(self.cleanup_db)

        cors = aiohttp_cors.setup(self.app)
        resource = cors.add(self.app.router.add_resource("/"))
        cors.add(
            resource.add_route("POST", self.handle), {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=False,
                    allow_headers=("X-Requested-With", "Content-Type"),
                    max_age=3600
                )
            }
        )

    def run(self):
        web.run_app(self.app, host="0.0.0.0", port=config.DAEMON_LISTENING_PORT)

    def create_passthrough(self, method):
        client = PassthroughClient()

        async def simple_passthrough(**kwargs):
            logger.debug("dispatching request to service")
            response = client.request(config.PASSTHROUGH_ENDPOINT, method, **kwargs)
            logger.debug("returning response to client")
            return response

        async def blockchain_passthrough(job_address=None, job_signature=None, **kwargs):
            job_address = self.chain.to_checksum_address(job_address)

            if job_address is None:
                logger.error("invalid request: job_address is required")
                raise InvalidParams("invalid request: job_address is required")

            if job_signature is None:
                logger.error("invalid request: job_signature is required")
                raise InvalidParams("invalid request: job_signature is required")

            if await self.chain.validate_job_invocation(job_address, job_signature):
                logger.debug("dispatching request to service; job_address: %s", job_address)
                response = client.request(config.PASSTHROUGH_ENDPOINT, method, **kwargs)
                db = self.app["db"]
                job_entry = db.get(job_address, {})
                job_entry["job_signature"] = job_signature
                job_entry["completed"] = True
                logger.debug("saving job to db; job_address: %s; db entry: %s", job_address, job_entry)
                db[job_address] = job_entry
                self.app.loop.create_task(self.chain.complete_job(job_address, job_signature))
                logger.debug("returning response to client; job_address: %s", job_address)
                return response
            else:
                logger.error("job invocation failed to validate")
                raise ServerError("job invocation failed to validate")

        if config.BLOCKCHAIN_ENABLED:
            return blockchain_passthrough
        else:
            return simple_passthrough

    async def process_completions(self, app):
        for k, v in app["db"].items():
            if isinstance(v, dict) and v.get("completed", False):
                app.loop.create_task(self.chain.complete_job(k, v.get("job_signature")))

    async def create_event_task(self, app):
        app["event_task"] = app.loop.create_task(self.chain.process_events())

    @staticmethod
    async def cancel_event_task(app):
        app["event_task"].cancel()

    @staticmethod
    async def handle(request):
        request = await request.text()
        response = await methods.dispatch(request)
        if response.is_notification:
            return web.Response()
        else:
            return web.json_response(response, status=response.http_status)

    @staticmethod
    async def setup_db(app):
        app["db"] = shelve.open(config.DB_PATH)

    @staticmethod
    async def cleanup_db(app):
        app["db"].close()


if __name__ == '__main__':
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s - [%(levelname)8s] - %(name)s - %(message)s")
    d = SingularityNetDaemon()
    d.run()
