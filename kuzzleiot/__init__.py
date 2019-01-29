from .iotdevice import IoTDevice, IoTDeviceInfo
from .kuzzlegateway import Gateway

import logging

LOG = logging.getLogger('Kuzzle-IoT')
LOG.setLevel(logging.DEBUG)

INDEX_IOT = "iot"
COLLECTION_DEVICE_STATES = "device-state"
COLLECTION_DEVICE_INFO = "device-info"


# __all__ = ["LOG", "iotdevice", "kuzzlegateway", "INDEX_IOT", "COLLECTION_DEVICE_INFO", "COLLECTION_DEVICE_STATES"]
