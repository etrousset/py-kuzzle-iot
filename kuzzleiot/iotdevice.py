import kuzzleiot.kuzzlegateway
import json
import logging

LOG = logging.getLogger('Kuzzle-IoT').getChild("dev")
JSON_DEC = json.JSONDecoder()


class IoTDeviceInfo:
    """
    This class represent the general information about a device
    as found in iot/device-info collection.
    """

    def __init__(self):
        self.friendly_name = str
        self.friendly_name = str
        self.geo_loc = None
        self.location = str
        self.owner = str
        self.sub_loc = str
        self.additional_info = dict


class IoTDevice(object):

    def __init__(self,
                 device_uid: str,
                 device_type: str,
                 gateway: kuzzleiot.kuzzlegateway.Gateway,
                 owner: str = None,
                 ):
        """
        Initializes a new instance of a KuzzleIOTDevice

        :param device_uid: The device unique ID
        :param device_type: The string identifying the device type
        :param gateway: The KuzzleIOTGateway object that allow communication to Kuzzle Server
        :param owner: The kuid of the owner
        """
        self.owner = owner

        self.device_uid = device_uid
        self.device_type = device_type
        self.on_connected = None
        self.on_state_changed = None
        self.gateway = gateway

    def get_device_info(self, cb: callable):
        """
        Retrieve the device information from Kuzzle Server
        :param cb:
        :return:
        """
        return self.gateway.get_device_info(self.device_uid, cb)

    def register_device(self, device_info: IoTDeviceInfo = None):
        """
        Register device in Kuzzle Server
        :param device_info: device detailed information (optional)
        :return:
        """
        LOG.info("Registering device...")
        return self.gateway.register_device(self, device_info)

    # def on_device_info_resp(self, resp):
    #     LOG.debug("device info result")
    #     if resp['status'] != 200:
    #         self.publish_device_info()

    def subscribe_state(self, on_state_changed: callable):
        LOG.debug("subscribing to own state")
        return self.gateway.subscribe_device_state(self.device_uid, on_state_changed)

    def publish_state(self, state, partial=False):
        LOG.debug("Publishing state")
        return self.gateway.publish_device_state(self.device_uid, self.device_type, state, partial)
