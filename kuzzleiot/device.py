import asyncio
import json
from kuzzleiot import *
from kuzzleiot.gateway import KuzzleIOTGateway

LOG = LOG.getChild("dev")


class KuzzleIOTDevice(object):
    JSON_DEC = json.JSONDecoder()

    def __init__(self,
                 device_uid: str,
                 device_type: str,
                 gateway: KuzzleIOTGateway,
                 owner: str = None,
                 friendly_name: str = None,
                 additional_info: dict = None
                 ):
        self.owner = owner
        self.friendly_name = friendly_name
        self.additional_info = additional_info

        self.device_uid = device_uid
        self.device_type = device_type
        self.on_connected = None
        self.on_state_changed = None
        self.gateway = gateway

    def get_device_info(self):
        return self.gateway.get_device_info(self.device_uid, self.on_device_info_resp)

    def publish_device_info(self):
        LOG.info("Publishing device info...")
        body = {
            'device_id': self.device_uid,
            'owner': self.owner,
            'friendly_name': self.friendly_name,
            'device_type': self.device_type,
        }

        if self.additional_info:
            body['additional_info'] = self.additional_info

        query = {
            "index": INDEX_IOT,
            "collection": COLLECTION_DEVICE_INFO,
            "requestId": REQUEST_PUBLISH_DEVICE_INFO,
            "controller": "document",
            "action": "createOrReplace",
            "_id": self.device_uid,
            "body": body
        }
        LOG.info("%s", query)
        self.gateway.post_query(query)

    def on_device_info_resp(self, resp):
        LOG.debug("device info result")
        if resp['status'] != 200:
            self.publish_device_info()

    def subscribe_state(self, on_state_changed: callable):

        LOG.debug("subscribing to own state")
        return self.gateway.subscribe_device_state(self.device_uid, on_state_changed)

    def publish_state(self, state, partial=False):
        LOG.debug("Publishing state")
        return self.gateway.publish_device_state(self.device_uid, self.device_type, state, partial)
