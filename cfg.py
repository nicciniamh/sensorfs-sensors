import os
import json
import tempfile

config = None

def get_config():
    global config
    if not config:
        with open('sensors.json') as f:
            config= json.load(f)
    return config

def get_sensors():
    return get_config()['sensors']

def get_sensor(name):
    return get_config()['sensors'][name]

def get_sensor_chart(name):
    return get_config()['sensors'][name]['chart']

def write_config():
    with open('sensors.json','w') as f:
        json.dump(get_config(),f,indent=4)

