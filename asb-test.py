import sck
import yaml
import json
import os
import sys
from pathlib import Path

# Smart Citizen Kit
kit = sck.sck()
kit.begin(get_sensors=True)
try:
    sensors_enabled = kit.sensor_enabled
except:
    print('There are no enabled sensors')

# Data files
folder_data = Path('../smartcitizen-data/')
file_hardware = folder_data / 'hardware/hardware.json'
file_calibrations = folder_data / 'scdata/utils/interim/calibrations.yaml'
try:
    with open(file_hardware, 'r') as file:
        data_hardware = json.load(file)
except:
    print('Hardware file not found. Expected location: ', file_hardware)
try:
    with open(file_calibrations, 'r') as file:
        data_calibrations = yaml.load(file, Loader=yaml.FullLoader)
except:
    print('Calibrations file not found. Expected location: ', file_calibrations)


# Sensor ID given manually by running this script
# for example: python3 test.py 001292129
if (len(sys.argv) == 2):
    kit_id = str(sys.argv[1])
    print('Kit ID: ' + kit_id)
elif (len(sys.argv) == 1):
    print('An ID must be provided')
else:
    print('Only one ID must be provided')

# Sensors basics
this_sensor = 'ADS1x15 ADC'
this_sensor_unit = 'V'
these_sensors = []
this_kit = {}

# Getting sensors
if 'sensors_enabled' in globals():
    for sensor in sensors_enabled:
        if this_sensor in sensor:
            these_sensors.append(sensor)

# Getting metrics
if len(these_sensors) > 0:
    these_sensors_metrics = kit.readSensors(
        sensors=these_sensors, iter_num=2, delay=0.1, unit=this_sensor_unit, method='avg')

if 'kit_id' in globals() and 'these_sensors_metrics' in globals():

    # Kit update
    this_kit[kit_id] = these_sensors_metrics

    # Text formatting (Ch0)
    new_keys = []
    for item in this_kit[kit_id]:
        item_formatted = item[-3:]
        new_keys.append(item_formatted)
    this_kit_formatted = {}
    this_kit_formatted[kit_id] = dict(
        zip(new_keys, list(this_kit[kit_id].values())))

# Getting ID's from hardware.json
if 'data_hardware' in globals() and 'kit_id' in globals():
    hardware_ids = data_hardware[list(data_hardware.keys())[1]]['1']['ids']

# Getting values from calibrations.yaml and update it
if 'data_calibrations' in globals() and 'hardware_ids' in globals():
    calibrations_values = {}
    data_index = 0
    for i in hardware_ids.values():
        data_index += 1
        try:
            calibrations_values[i] = data_calibrations[i]
            if (data_index == 1):
                calibrations_values[i]['ae_electronic_zero_mv'] = str(this_kit_formatted[kit_id].get('Ch0'))
                calibrations_values[i]['we_electronic_zero_mv'] = str(this_kit_formatted[kit_id].get('Ch1'))
            elif (data_index == 2):
                calibrations_values[i]['ae_electronic_zero_mv'] = str(this_kit_formatted[kit_id].get('Ch2'))
                calibrations_values[i]['we_electronic_zero_mv'] = str(this_kit_formatted[kit_id].get('Ch3'))
        except:
            print('Sensor ID', i, 'does not exist')
    
    # Update the calibrations file
    data_calibrations.update(calibrations_values)
    with open(file_calibrations, 'w') as file:
        yaml.dump(data_calibrations, file, default_flow_style=False)
