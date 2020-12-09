import sck
import yaml
import json
import os
import sys
import traceback
from pathlib import Path

do_test = False

# Smart Citizen Kit
kit = sck.sck()
kit.begin(get_sensors=True)
try:
    sensors_enabled = kit.sensor_enabled
    do_test = True
except:
    print('There are no enabled sensors')

# Data files
if do_test:
    folder_data = Path('../smartcitizen-data/')
    file_hardware = folder_data / 'hardware/hardware.json'
    file_calibrations = folder_data / 'scdata/utils/interim/calibrations.yaml'
    try:
        with open(file_hardware, 'r') as file:
            data_hardware = json.load(file)
    except:
        print('Hardware file not found. Expected location: ' + str(file_hardware))
        do_test = False
    try:
        with open(file_calibrations, 'r') as file:
            data_calibrations = yaml.load(file, Loader=yaml.FullLoader)
    except:
        print('Calibrations file not found. Expected location: ' +
              str(file_calibrations))
        do_test = False

# Sensor ID given manually by running this script
# for example: python3 test.py 001292129
if do_test:
    if (len(sys.argv) == 2):
        kit_id = str(sys.argv[1])
        print('Kit ID: ' + str(kit_id))
    elif (len(sys.argv) == 1):
        print('An ID must be provided')
        do_test = False
    else:
        print('Only one ID must be provided')
        do_test = False


if do_test:

    # Sensors basics
    this_sensor = 'ADS1x15 ADC'
    these_sensors = []
    this_kit = {}
    for sensor in sensors_enabled:
        if this_sensor in sensor:
            these_sensors.append(sensor)
    # Getting metrics
    these_sensors_metrics = kit.readSensors(
        sensors=these_sensors, iter_num=2, delay=0.1, unit='V', method='avg')

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

    # # From V to mV, rounded
    # for item in this_kit_formatted[kit_id]:
    #     this_kit_formatted[kit_id][item] = round(
    #         this_kit_formatted[kit_id][item] * 1000, 2)

    # Getting ID's from hardware.json
    hardware_ids = data_hardware[kit_id]['1']['ids']

    # Getting values from calibrations.yaml and update it
    calibrations_values = {}
    data_index = 0
    for i in hardware_ids.values():
        data_index += 1
        try:
            calibrations_values[i] = data_calibrations[i]
            if (data_index == 1):
                calibrations_values[i]['ae_electronic_zero_mv'] = str(
                    this_kit_formatted[kit_id].get('Ch0'))
                calibrations_values[i]['we_electronic_zero_mv'] = str(
                    this_kit_formatted[kit_id].get('Ch1'))
            elif (data_index == 2):
                calibrations_values[i]['ae_electronic_zero_mv'] = str(
                    this_kit_formatted[kit_id].get('Ch2'))
                calibrations_values[i]['we_electronic_zero_mv'] = str(
                    this_kit_formatted[kit_id].get('Ch3'))
        except:
            print('Sensor #' + str(i) + ' does not exist in ' +
                  str(file_calibrations))

    # Update the calibrations file
    data_calibrations.update(calibrations_values)
    with open(file_calibrations, 'w') as file:
        yaml.dump(data_calibrations, file, default_flow_style=False)
    print('Calibrations file updated (' + str(file_calibrations) + ')')
