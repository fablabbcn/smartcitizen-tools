import sck
import yaml
import os
import sys
from pathlib import Path

# Data files
folder_data = Path("../smartcitizen-data/scdata/utils/interim/")
file_blueprints = folder_data / "blueprints.yaml"
file_calibrations = folder_data / "calibrations.yaml"
data_blueprints = open(file_blueprints)
data_calibrations = open(file_calibrations)

# Sensor ID given manually
try:
    sensors_id = str(sys.argv[1])
except:
    print('An ID must be provided')

# Files calibrations.yaml and blueprints.yaml
file_calibrations = "calibrations.yaml"
file_blueprints = "blueprints.yaml"


# My sensors
my_sensor = 'ADS1x15 ADC'
my_sensor_unit = 'V'
my_sensors = []

# Kit
kit = sck.sck()
kit.begin(get_sensors=True)
sensors_enabled = kit.sensor_enabled
serial_number = kit.serialNumber
my_kit = {}

# Get my sensors
for sensor in sensors_enabled:
    if my_sensor in sensor:
        my_sensors.append(sensor)

# Get the metrics
my_sensors_metrics = kit.readSensors(
    sensors=my_sensors, iter_num=2, delay=0.1, unit=my_sensor_unit, method='avg')

if my_sensors_metrics:
    # Update my kit
    my_kit[serial_number] = my_sensors_metrics
    # Format text (ADC_48_0)
    new_keys = []
    for item in my_kit[serial_number]:
        item_formatted = item.replace('ADS1x15', '').replace(
            'Ch', '').replace('0x', '').strip().replace(' ', '_')
        new_keys.append(item_formatted)
    my_kit_formatted = {}
    my_kit_formatted[serial_number] = dict(
        zip(new_keys, list(my_kit[serial_number].values())))
    # Update YAML file
    results_file = "test-results.yml"
    file_values = {}

    if not os.path.exists(results_file):
        # create the file if it doesn't exist yet
        os.mknod(results_file)

    # If not empty, get the values from it
    if not os.stat(results_file).st_size == 0:
        with open(results_file, 'r') as file:
            file_values = yaml.load(file, Loader=yaml.FullLoader)

    # Update the values with those in the file
    file_values.update(my_kit_formatted)
    # Re write the file
    with open(results_file, 'w') as file:
        yaml.dump(file_values, file, default_flow_style=False)

    print('')
    print('')
    print("Values of this kit:")
    print('----------------------------')
    print(my_sensors_metrics)
    print('')
    print('')
    print("All values:")
    print('----------------------------')
    print(file_values)
    print('')
    print('')
else:
    print('The sensor returned an empty value')
    print('It needs to be checked')
