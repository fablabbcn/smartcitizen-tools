import sck
import json
import os
import sys
import traceback
import time
from tqdm import tqdm

do_test = True

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

def oneLine(msg):
    enablePrint()
    sys.stdout.write(msg)
    sys.stdout.flush()
    if not verbose: blockPrint()

def enablePrint():
    sys.stdout = sys.__stdout__

verbose = False
blockPrint()
if '-v' in sys.argv:
    verbose = True
    enablePrint()

if '-h' in sys.argv:
    print ('Help:')
    print ('co2.py')
    print ('-v: verbose')
    print ('--dry-run: updates sensor calibration')
    print ('--margin: margin in ppms for recalibration check (20 ppm)')
    print ('--stab-time: stabilisation time in seconds (120s)')

# Smart Citizen Kit
kit = sck.sck()
kit.begin(get_sensors=True)
kit.getSensors()
kit.getNetInfo()
kit.getVersion()

dry_run = False
if '--dry-run' in sys.argv:
    dry_run = True

margin = 20
if '--margin' in sys.argv:
    margin = int(sys.argv[sys.argv.index('--margin')+1])
print (f'Using margin for offset: {margin}ppm')

stab_time = 120
if '--stab-time' in sys.argv:
    stab_time = int(sys.argv[sys.argv.index('--stab-time')+1])
print (f'Using stabilisation time for sensor: {stab_time}s')

if 'DATA_PATH' in os.environ: folder_data = os.environ['DATA_PATH']
else: print ('DATA_PATH variable not defined in environment'); exit()

# folder_data = Path('../smartcitizen-data/')

file_calibrations = os.path.join(folder_data, 'calibrations/co2.json')
try:
    with open(file_calibrations, 'r') as file:
        calibrations = json.load(file)
except:
    print('Calibrations file not found. Expected location: ' +
          str(file_calibrations))
    do_test = False

    traceback.print_exc()

if kit.esp_macAddress is None:
    do_test = False

if str(kit.esp_macAddress) not in calibrations:
    do_test = False
    print(f'MAC not in calibrations ({kit.esp_macAddress})')

file_done = os.path.join(folder_data, 'calibrations/done.txt')

done_sensors = open(file_done, "r")
if kit.esp_macAddress in done_sensors:
    print (f'MAC Address already in done ({kit.esp_macAddress})')
    do_test = False

if do_test:
    # Sensors basics
    co2_sensor = 'SCD30 CO2'

    offset = calibrations[kit.esp_macAddress]

    sensors = []
    for sensor in kit.sensor_enabled:
        if co2_sensor in sensor:
            sensors.append(sensor)
    print (f'MAC: {kit.esp_macAddress}')
    # TODO wait for sensor to stabilise here
    for i in tqdm (range (100),
               desc="Stabilising sensor...",
               ascii=False, ncols=50):
        time.sleep(stab_time/100)

    while True:

        print ('Initial reading')
        # Getting metrics
        initial_reading = kit.readSensors(
            sensors=sensors, iter_num=5, delay=1, method='avg', unit='ppm')
        print ('---------------')

        print (initial_reading)
        print ('---------------')

        msg = f'control scd30 calfactor {round(initial_reading[co2_sensor] + offset)}'

        if dry_run: print (msg)
        else:
            for item in kit.sendCommand(msg):
                print (item)
            print ('---------------')

            time.sleep(5)
            print ('Final reading')
            final_reading = kit.readSensors(
                sensors=sensors, iter_num=5, delay=1, method='avg', unit='ppm')
            print ('---------------')

            print (final_reading)

            if ((initial_reading[co2_sensor] + offset + margin) < final_reading[co2_sensor]) or\
                ((initial_reading[co2_sensor] + offset - margin) > final_reading[co2_sensor]):
                print (f'Final reading out of margin ({margin} ppm)')
                while True:
                    what_to_do = input('Repeat? [y/n]: ')
                    if what_to_do == 'y' or what_to_do == 'n':
                        break
                    else:
                        print ('Please input [y/n]')

                if what_to_do == 'n':
                    with open(file_done, 'a') as f:
                        f.write(kit.esp_macAddress)
                    break
            else:
                with open(file_done, 'a') as f:
                    f.write(kit.esp_macAddress)
                break

    print ('Done!')
