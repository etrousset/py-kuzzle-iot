# py-kuzzle-iot

Python3 client for [Kuzzle](https://github.com/kuzzleio/kuzzle) IoT environment as described at   [kuzzle-iot-deploy](https://github.com/etrousset/kuzzle-iot-deploy) 

## Usage

### Instantiate and connect to *Kuzzle*

```python
my_device = KuzzleIOT(
    my_device_uid,
    "my-device-type",
    host=kuzzle_conf['host'],
    port=kuzzle_conf['port'],
    owner=config["device"]["owner"]
)

my_device.connect(on_kuzzle_connected_cb)
```

### Publish device state to *Kuzzle*

```python
my_device.publish_state(my_device_state)
```
### Subscribe to device changes through *Kuzzle*
```python
def on_state_change_cb(self, state, is_partial):
    # TODO: merge or replace my device state with the one from Kuzzle


my_device.subscribe_state(on_state_change_cb)
```
