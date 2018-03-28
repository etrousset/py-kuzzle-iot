import time
from typing import Union

import websockets.client
import websockets.exceptions as wse
import requests

import asyncio
import json
import uuid

from numpy.lib.utils import source

from kuzzleiot import *

LOG = LOG.getChild("gw")


class KuzzleIOTGateway(object):
    JSON_DEC = json.JSONDecoder()

    def __init__(self, host='localhost', port='7512', user: str = '', pwd: str = ''):
        self.event_loop = None
        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.disconnecting = False
        self.uuid = str(uuid.uuid4())

        self.url = "ws://{}:{}".format(self.host, self.port)

        self.ws = None
        self.on_connected = None

        self.device_state_changed_cbs = {}
        self.device_info_cbs = {}

        # coloredlogs.install(logger=KuzzleIOT.LOG,
        #                     fmt='[%(thread)X] - %(asctime)s - %(name)s - %(levelname)s - %(message)s',
        #                     level=logging.DEBUG,
        #                     stream=sys.stdout)

    @staticmethod
    def server_info(host='localhost', port='7512') -> Union[dict, None]:
        """
        Get Kuzzle server information. This can be used to validate we are able to reach the server
        """

        url = "http://{}:{}/_serverInfo".format(host, port)
        try:
            req = requests.get(url=url)
            res = json.JSONDecoder().decode(req.text)
            # json.dump(res, sys.stdout, indent=2)
            if res["status"] == 200:
                return res["result"]
            else:
                LOG.critical('Unable to connect to Kuzzle: http://%s:%s', host, port)
                LOG.error(res["error"]["message"])
                LOG.error(res["error"]["stack"])
                return None
        except Exception as e:
            LOG.critical('Unable to connect to Kuzzle: http://%s:%s', host, port)
            return None

    def __publish_request_id(self):
        return REQUEST_PUBLISH_DEVICE_STATE + self.uuid

    async def __publish_device_state_task(self, device_uid: str, device_type: str, state: dict, partial: bool):
        body = {
            "device_id": device_uid,
            "device_type": device_type,
            "partial_state": partial,
            "state": state
        }

        req = {
            "index": INDEX_IOT,
            "collection": COLLECTION_DEVICE_STATES,
            "requestId": self.__publish_request_id(),
            "controller": "document",
            "action": "create",
            "body": body
        }
        t = self.post_query(req)
        LOG.debug("PUBLISH >>>>")
        return t

    async def __subscribe_device_state_task(self, device_uid: str, on_state_changed: callable):

        self.device_state_changed_cbs[device_uid] = on_state_changed
        subscribe_msg = {
            "index": INDEX_IOT,
            "collection": COLLECTION_DEVICE_STATES,
            "controller": "realtime",
            "action": "subscribe",
            "body": {
                "equals": {
                    "device_id": device_uid
                }
            }
        }

        return self.post_query(subscribe_msg)

    async def __connect_task(self, on_connected: callable):
        LOG.debug("<Connecting.... url = %s>", self.url)
        try:
            self.ws = await websockets.client.connect(self.url)
        except Exception as e:
            LOG.critical(e)
            return

        LOG.info("<Connected to %s>", self.url)

        self.on_connected = on_connected

        if self.on_connected:
            self.on_connected(self)

        # self.get_device_info()

        self.__run_loop_start()

    def __connect(self, on_connected: callable):
        return self.event_loop.create_task(self.__connect_task(on_connected))

    def __run_loop_start(self):
        self.loop = self.event_loop.create_task(self.__reader_task())

    def on_device_info_resp(self, resp):
        LOG.debug(" device info result")
        req_id = resp["requestId"]
        if self.device_info_cbs[req_id]:
            self.device_info_cbs[req_id](resp)
            del self.device_info_cbs[req_id]

            # if resp['status'] != 200:
            #     self.publish_device_info()

    async def __reader_task(self):
        while 1:
            LOG.debug("<<Waiting for data from Kuzzle...>>")
            try:
                resp = await asyncio.wait_for(self.ws.recv(), timeout=60)
            except wse.ConnectionClosed as e:
                if self.disconnecting:
                    LOG.debug("Stopping reader task")
                    return

                LOG.warning('ws disconnection: %s', str(e))
                LOG.info('reconnecting in 5s...')
                time.sleep(5)

                try:
                    # FIXME: Device states resubscribing
                    self.ws = await websockets.connect(self.url)
                    # TODO: LOG.debug('Re subscribing to own state...')
                    # TODO: self.subscribe_state(self.on_state_changed)
                except Exception as e:
                    LOG.critical(e)
                continue
            except asyncio.TimeoutError:
                try:
                    LOG.info("PING Kuzzle")
                    pong_waiter = await self.ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    LOG.info("PONG Kuzzle")
                except asyncio.TimeoutError:
                    LOG.critical("No PONG from Kuzzle")
                    break
                continue
            except Exception as e:
                LOG.error('__publish_state_task: ws except: %s', str(e))

            LOG.debug("<<Received data from Kuzzle...>>")
            resp = json.loads(resp)
            LOG.debug(json.dumps(resp, indent=2, sort_keys=True))

            if resp["status"] != 200:
                LOG.warning("resp = %s", json.dumps(resp, indent=2, sort_keys=True))

            if resp["action"] in ['replace', 'create'] \
                    and resp["requestId"] != self.__publish_request_id():

                _source = resp["result"]["_source"]
                if self.device_state_changed_cbs[_source["device_id"]]:
                    LOG.debug("Received a device state: %s", str(_source))
                    is_partial = _source["is_partial"] if "state_partial" in _source else False
                    self.device_state_changed_cbs[_source["device_id"]](_source["state"], is_partial)

            elif resp['requestId'].startswith(REQUEST_GET_DEVICE_INFO):
                self.on_device_info_resp(resp)

        LOG.warning("Quitting reader task...")

    def subscribe_device_state(self, device_uid: str, on_state_changed: callable):
        LOG.debug("<<Adding task to subscribe to device state: %s>>", device_uid)
        return self.event_loop.create_task(
            self.__subscribe_device_state_task(device_uid, on_state_changed)
        )

    async def __post_query_task(self, query: dict, cb: callable = None):
        LOG.debug("Posting query: %s", json.dumps(query))
        await self.ws.send(json.dumps(query))
        if cb:
            cb()
        LOG.debug("Query posted")

    def post_query(self, query: dict, cb: callable = None):
        LOG.debug("<<Adding task to post a query>>")
        return self.event_loop.create_task(self.__post_query_task(query, cb))

    def get_device_info(self, device_uid: str, cb: callable):
        query = {
            "index": INDEX_IOT,
            "collection": COLLECTION_DEVICE_INFO,
            "requestId": REQUEST_GET_DEVICE_INFO + device_uid,
            "controller": "document",
            "action": "get",
            '_id': device_uid
        }

        if cb:
            self.device_info_cbs[REQUEST_GET_DEVICE_INFO + device_uid] = cb
        return self.post_query(query)

    def publish_device_state(self, device_uid: str, device_type: str, state: dict, partial=False):
        LOG.debug("%s: <<Adding task to publish state>>")
        return asyncio.run_coroutine_threadsafe(
            self.__publish_device_state_task(device_uid, device_type, state, partial),
            self.event_loop
        )

    def connect(self, on_connected: callable = None):
        LOG.debug("<Connect>")
        self.event_loop = asyncio.get_event_loop()
        assert self.event_loop, "No event loop found"
        return self.__connect(on_connected)

    def disconnect(self):
        LOG.debug("Disconnecting from Kuzzle...")
        self.disconnecting = True
        asyncio.get_event_loop().run_until_complete(self.ws.close())
        LOG.debug("Disconnected")
