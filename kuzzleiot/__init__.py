import logging

LOG = logging.getLogger('Kuzzle-IoT')
LOG.setLevel(logging.DEBUG)

INDEX_IOT = "iot"
COLLECTION_DEVICE_STATES = "device-state"
COLLECTION_DEVICE_INFO = "device-info"

REQUEST_PUBLISH_DEVICE_INFO = "publish_device_info"
REQUEST_PUBLISH_DEVICE_STATE = "publish_"
REQUEST_GET_DEVICE_INFO = "get_device_info"
