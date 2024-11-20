'''
Smartcitizen Kit python library.
This library is meant to be run inside the firmware repository folder.
'''

import os
import subprocess
try:
    import uf2conv
except ModuleNotFoundError:
    print('Cannot import uf2conv module')
    pass
import shutil
import binascii
import json
import requests
import traceback
import sys
import options

from os import name
_mswin = name == 'nt'

try:
    from serialtools.serialdevice import *
except ModuleNotFoundError:
    try:
        from src.tools.serialtools.serialdevice import *
    except:
        print('Cannot import serialdevice')
        traceback.print_exc()
        pass

class sck(serialdevice):

    def __init__(self, to_register=False, verbose=2):
        super().__init__(device_type='sck')
        self.sensors = []
        # 0 -> never print anything, 1 -> print only errors, 2 -> print everything
        self.verbose = verbose

        if to_register == False:
            # paths
            self.paths = {}
            self.paths['base'] = str(subprocess.check_output(
                ['git', 'rev-parse', '--show-toplevel']).rstrip().decode('utf-8'))
            self.paths['binFolder'] = os.path.join(
                str(self.paths['base']), 'bin')
            if not os.path.exists(self.paths['binFolder']):
                os.mkdir(self.paths['binFolder'])
            self.paths['esptoolPy'] = os.path.join(
                str(self.paths['base']), 'tools', 'esptool.py')

            # Get envs
            self.envs = {
                'sam': {},
                'esp': {}
                }

            os.chdir('sam')
            for s in subprocess.check_output(['pio', 'run', '-t', 'envdump']).decode('utf-8').split('\n'):
                if "'PIOENV'" in s:
                    name = s.split()[1].strip(',').strip("'")
                    self.envs['sam'][s.split()[1].strip(',').strip("'")]={
                        'samBin': f'SAM_firmware_{name}.bin',
                        'samHex': f'SAM_firmware_{name}.hex',
                        'samUf2': f'SAM_firmware_{name}.uf2'
                    }

            # Get pioHome Path
            os.chdir(os.path.join(self.paths['base'], 'esp'))
            for s in subprocess.check_output(['pio', 'run', '-t', 'envdump']).decode('utf-8').split('\n'):
                if "'PIOENV'" in s:
                    self.envs['esp'][s.split()[1].strip(',').strip("'")]={'espBin': 'ESP_firmware.bin'}
                elif "'PROJECT_PACKAGES_DIR'" in s:
                    self.paths['pioHome'] = s.split()[1].strip(',').strip("'")

            os.chdir(self.paths['base'])
            self.paths['esptool'] = os.path.join(
                str(self.paths['pioHome']), '', 'tool-esptool', 'esptool')

            print ('--PATHS--')
            print (self.paths)
            print ('--ENVS--')
            print (self.envs)

    # Serial port
    serialPort = None
    serialPort_name = None

    # chips and firmware info
    versionReady = False
    netInfoReady = False
    sam_serialNum = ''
    sam_firmVer = ''
    sam_firmCommit = ''
    sam_firmBuildDate = ''
    esp_macAddress = ''
    esp_sta_macAddress = ''
    hostname = ''
    esp_firmVer = ''
    esp_firmCommit = ''
    esp_firmBuildDate = ''

    # WiFi and platform info
    mode = ''
    token = ''
    wifi_ssid = ''
    wifi_pass = ''

    is_test = False
    postprocessing_meta = None

    def begin(self, get_sensors=False, port=None, force=False):
        if self.set_serial(port=port, force=force):
            if get_sensors:
                for retry in range(3):
                    if self.getSensors():
                        break
                    return False
        else:
            return False

        self.sam_serialNum = self.serialNumber
        return True

    def checkConsole(self):
        timeout = time.time() + 15
        while True:
            self.serialPort.write('\r\n'.encode())
            time.sleep(0.1)
            # buff = self.serialPort.read(self.serialPort.in_waiting).decode("utf-8")
            buff = self.read_all_serial(chunk_size=200).decode('utf-8')
            if 'SCK' in buff:
                return True
            if time.time() > timeout:
                self.err_out('Timeout waiting for kit console response')
                return False
            time.sleep(0.5)

    def getVersion(self):
        if self.versionReady:
            return
        self.update_serial()
        self.serialPort.write('\r\nversion\r\n'.encode())
        time.sleep(0.5)
        for item in self.read_all_serial(chunk_size=200).decode('utf-8').split('\n'):
            if 'SAM version:' in item:
                self.sam_firmVer = item.split(': ')[1].strip('\r')
            if 'ESP version:' in item:
                self.esp_firmVer = item.split(': ')[1].strip('\r')
        self.versionReady = True

    def getNetInfo(self):
        if self.netInfoReady:
            return
        self.update_serial()
        self.serialPort.write('\r\nnetinfo\r\n'.encode())
        time.sleep(0.5)
        for item in self.read_all_serial(chunk_size=200).decode('utf-8').split('\n'):
            if 'AP MAC address:' in item:
                self.esp_macAddress = item.split(': ')[1].strip('\r')
            if 'STA MAC address:' in item:
                self.esp_sta_macAddress = item.split(': ')[1].strip('\r')
            if 'Hostname:' in item:
                self.hostname = item.split(': ')[1].strip('\r')
        self.netInfoReady = True

    def getConfig(self):
        self.update_serial()
        self.checkConsole()
        self.serialPort.write('\r\nconfig\r\n'.encode())
        time.sleep(0.5)
        m = self.read_all_serial(chunk_size=200).decode('utf-8')
        for line in m.split('\n'):
            if 'Mode' in line:
                mm = line.split('Mode: ')[1].strip()
                if mm != 'not configured':
                    self.mode = mm
            if 'Token:' in line:
                tt = line.split(':')[1].strip()
                if tt != 'not configured' and len(tt) == 6:
                    self.token = tt
            if 'credentials:' in line:
                ww = line.split('credentials: ')[1].strip()
                if ww.count(' - ') == 1:
                    self.wifi_ssid, self.wifi_pass = ww.split(' - ')
                    if self.wifi_pass == 'null':
                        self.wifi_pass = ""

    def getSensors(self):

        self.update_serial()
        self.checkConsole()
        self.serialPort.write('sensor\r\n'.encode())

        m = self.read_all_serial(chunk_size=200).decode("utf-8").split('\r\n')

        while '----------' in m:
            m.remove('----------')
        while 'SCK > ' in m:
            m.remove('SCK > ')

        self.sensor_enabled = dict()
        if 'Enabled' in m:
            for key in m[m.index('Enabled')+1:]:
                name = key[:key.index('-')]
                # Sensor[name]: interval
                self.sensor_enabled[name[:-1]] = key[key.index('(') + 1:-1]
            self.sensor_disabled = m[m.index('Disabled')+1:m.index('Enabled')]

            return True
        else:
            return False

    def sendCommand(self, msg):
        self.update_serial()
        self.checkConsole()

        self.std_out('Sending command: ' + msg)
        command = msg + '\r\n'
        self.serialPort.write(command.encode())

        return self.read_all_serial(chunk_size=200).decode("utf-8").split('\r\n')

    def enableSensor(self, sensor):
        self.update_serial()
        self.checkConsole()
        self.getSensors()

        if sensor in self.sensor_enabled.keys():
            self.std_out('Sensor already enabled', 'WARNING')
            return True

        else:
            self.std_out('Enabling sensor ' + sensor)
            command = 'sensor -enable ' + sensor + '\r\n'
            self.serialPort.write(command.encode())

            self.getSensors()
            print(self.sensor_enabled.keys())
            if sensor in self.sensor_enabled.keys():
                return True
            else:
                return False

    def disableSensor(self, sensor):
        self.update_serial()
        self.checkConsole()
        self.getSensors()

        if sensor in self.sensor_enabled.keys():
            self.std_out('Sensor already enabled', 'WARNING')
            return True

        else:
            self.std_out('Disabling sensor ' + sensor)
            command = 'sensor -disable ' + sensor + '\r\n'
            self.serialPort.write(command.encode())

            self.getSensors()
            if sensor in self.sensor_disabled:
                return True
            else:
                return False

    def sleep(self):
        self.update_serial()
        self.checkConsole()

        self.std_out('Sending to sleep mode')
        command = '\r\nsleep\r\n'
        self.serialPort.write(command.encode())


    def toggleShell(self):
        self.update_serial()
        self.checkConsole()

        if not self.statusShell():
            self.std_out('Setting shell mode')
            command = '\r\nshell -on\r\n'
            self.serialPort.write(command.encode())
        else:
            self.std_out('Setting normal mode')
            command = '\r\nshell -off\r\n'
            self.serialPort.write(command.encode())

    def statusShell(self):
        self.update_serial()
        self.checkConsole()

        self.serialPort.write('shell\r\n'.encode())
        time.sleep(0.5)
        m = self.read_all_serial().decode("utf-8").split('\r\n')
        for line in m:
            if 'Shell mode' in line:
                if 'off' in line:
                    return False
                if 'on' in line:
                    return True

    def readSensors(self, sensors=None, iter_num=1, delay=0, method='avg', unit=''):
        self.update_serial()
        self.checkConsole()
        self.getSensors()
        sensors_readings = {}

        if sensors is not None:
            print('Reading sensors:')
            for sensor in sensors:
                command = 'read ' + sensor + '\n'
                readings = []

                if sensor not in self.sensor_enabled:
                    if not self.enableSensor(sensor):
                        self.err_out(f'Cannot enable {sensor}')
                        return False

                for i in range(iter_num):
                    self.serialPort.write(command.encode())
                    self.serialPort.readline()
                    response = self.read_line()
                    response_formatted = response[0][len(sensor)+2:]
                    response_formatted = response_formatted.replace(' ' + unit, '')
                    readings.append(float(response_formatted))
                    print(str(sensor) + ': ' + str(i + 1) + '/' +
                          str(iter_num) + ' (' + str(response_formatted) + ' ' + str(unit) + ')')
                    time.sleep(delay)

                if method == "avg":
                    metric = sum(readings)/len(readings)
                elif method == "max":
                    metric = max(readings)
                elif method == "min":
                    metric = min(readings)

                # From V to mV, rounded
                metric = round(metric, 2)

                sensors_readings[sensor] = metric

            return sensors_readings

    def monitor(self, sensors=None, noms=True, notime=False, sd=False):
        import pandas as pd

        self.update_serial()
        self.checkConsole()
        self.getSensors()

        command = 'monitor '
        if noms:
            command = command + '-noms '
        if notime:
            command = command + '-notime '
        if sd:
            command = command + '-sd '

        if type(sensors) != list:
            sensors = sensors.split(',')
        if sensors is not None:
            for sensor in sensors:
                if sensor not in self.sensor_enabled:
                    if not self.enableSensor(sensor):
                        self.err_out(f'Cannot enable {sensor}')
                        return False
                command = command + sensor + ', '
            command = command + '\n'

        self.serialPort.write(command.encode())
        self.serialPort.readline()

        # Get columns
        columns = self.read_line()
        df_empty = dict()
        for column in columns:
            df_empty[column] = []
        # if not notime:
        df = pd.DataFrame(df_empty, columns=columns)
        # df.set_index('Time', inplace = True)
        # columns.remove('Time')

        self.start_streaming(df)

    def setBootLoaderMode(self):
        self.update_serial()
        self.serialPort.close()
        self.serialPort = serial.Serial(self.serialPort_name, 1200)
        self.serialPort.setDTR(False)
        time.sleep(5)
        mps = uf2conv.get_drives()
        for p in mps:
            if 'INFO_UF2.TXT' in os.listdir(p):
                return p
        self.err_out('Cant find the SCK mount point')
        return False

    def buildSAM(self, out=sys.__stdout__, env = 'sck2'):
        os.chdir(self.paths['base'])
        os.chdir('sam')
        # Choose a variant to build. Default is the sck2 only
        if env == 'all':
            piorun = subprocess.call(['pio', 'run'], stdout=out, stderr=subprocess.STDOUT)
            envs = self.envs['sam']
        else:
            piorun = subprocess.call(['pio', 'run', '-e', env], stdout=out, stderr=subprocess.STDOUT)
            envs = {env: self.envs['sam']}

        if piorun == 0:
            for _env in envs:
                try:
                    if os.path.exists(os.path.join(os.getcwd(), '.pioenvs', _env, 'firmware.bin')):
                        shutil.copyfile(os.path.join(os.getcwd(), '.pioenvs', _env, 'firmware.bin'), os.path.join(self.paths['binFolder'], self.envs['sam'][_env]['samBin']))
                        if os.path.exists(os.path.join(os.getcwd(), '.pioenvs', _env, 'firmware.hex')):
                            shutil.copyfile(os.path.join(os.getcwd(), '.pioenvs', _env, 'firmware.hex'), os.path.join(self.paths['binFolder'], self.envs['sam'][_env]['samHex']))
                    elif os.path.exists(os.path.join(os.getcwd(), '.pio/build', _env, 'firmware.bin')):
                        shutil.copyfile(os.path.join(os.getcwd(), '.pio/build', _env, 'firmware.bin'), os.path.join(self.paths['binFolder'], self.envs['sam'][_env]['samBin']))
                        if os.path.exists(os.path.join(os.getcwd(), '.pio/build', _env, 'firmware.hex')):
                            shutil.copyfile(os.path.join(os.getcwd(), '.pio/build', _env, 'firmware.hex'), os.path.join(self.paths['binFolder'], self.envs['sam'][_env]['samHex']))

                except:
                    self.err_out('Failed building SAM firmware')
                    return False
                # Write UF2
                with open(os.path.join(self.paths['binFolder'], self.envs['sam'][_env]['samBin']), mode='rb') as myfile:
                    inpbuf = myfile.read()
                outbuf = uf2conv.convert_to_uf2(inpbuf)
                uf2conv.write_file(os.path.join(
                    self.paths['binFolder'], self.envs['sam'][_env]['samUf2']), outbuf)

        os.chdir(self.paths['base'])
        return True

    def flashSAM(self, out=sys.__stdout__, env='sck2'):
        os.chdir(self.paths['base'])
        mountpoint = self.setBootLoaderMode()
        self.std_out(f"\nFlashing file: {self.envs['sam'][env]['samUf2']}")
        try:
            shutil.copyfile(os.path.join(self.paths['binFolder'], self.envs['sam'][env]['samUf2']), os.path.join(mountpoint, self.envs['sam'][env]['samUf2']))
        except:
            self.err_out('Failed transferring firmware to SAM')
            return False
        time.sleep(2)
        return True

    def getBridge(self, speed=921600):
        timeout = time.time() + 15
        while True:
            self.update_serial(speed)
            self.serialPort.write('\r\n'.encode())
            time.sleep(0.1)
            buff = self.read_all_serial(chunk_size=200).decode('utf-8')
            if 'SCK' in buff:
                break
            if time.time() > timeout:
                self.err_out('Timeout waiting for SAM bridge')
                return False
            time.sleep(2.5)
        buff = self.serialPort.read(self.serialPort.in_waiting)
        self.serialPort.write(('esp -flash ' + str(speed) + '\r\n').encode())
        time.sleep(0.2)
        buff = self.serialPort.read(self.serialPort.in_waiting)
        return True

    def buildESP(self, out=sys.__stdout__):
        os.chdir(self.paths['base'])
        os.chdir('esp')
        piorun = subprocess.call(
            ['pio', 'run'], stdout=out, stderr=subprocess.STDOUT)
        if piorun == 0:
            for env in self.envs['esp']:
                print (env)
                try:
                    if os.path.exists(os.path.join(os.getcwd(), '.pioenvs', env, 'firmware.bin')):
                        shutil.copyfile(os.path.join(os.getcwd(), '.pioenvs', env, 'firmware.bin'), os.path.join(self.paths['binFolder'], self.envs['esp'][env]['espBin']))
                    elif os.path.exists(os.path.join(os.getcwd(), '.pio/build', env, 'firmware.bin')):
                        shutil.copyfile(os.path.join(os.getcwd(), '.pio/build', env, 'firmware.bin'), os.path.join(self.paths['binFolder'], self.envs['esp'][env]['espBin']))
                except:
                    self.err_out('Failed building ESP firmware')
                    return False
            return True
        self.err_out('Failed building ESP firmware')
        return False

    def flashESP(self, speed=921600, out=sys.__stdout__, env='esp12e'):
        os.chdir(self.paths['base'])
        if not self.getBridge(speed):
            return False
        self.std_out(f"\nFlashing file: {self.envs['esp'][env]['espBin']}")
        # Close port if in Windows
        if _mswin: self.serialPort.close()

        flashedESP = subprocess.call([self.paths['esptool'], '-cp', self.serialPort_name, '-cb', str(speed), '-ca', '0x000000',
                                      '-cf', os.path.join(self.paths['binFolder'], self.envs['esp'][env]['espBin'])], stdout=out, stderr=subprocess.STDOUT)
        if flashedESP == 0:
            # Note: increased sleep time to leave some extra margin for slower systems
            time.sleep(3)
            return True
        else:
            self.err_out('Failed transferring ESP firmware')
            return False

    def eraseESP(self):
        if not self.getBridge():
            return False
        flashedESPFS = subprocess.call(
            [self.paths['esptoolPy'], '--port', self.serialPort_name, 'erase_flash'], stderr=subprocess.STDOUT)
        if flashedESPFS == 0:
            time.sleep(1)
            return True
        else:
            return False

    def reset(self):
        self.update_serial()
        self.checkConsole()
        self.serialPort.write('\r\n')
        self.serialPort.write('reset\r\n')

    def netConfig(self):
        if len(self.wifi_ssid) == 0 or len(self.token) != 6:
            self.err_out('WiFi and token MUST be set!!')
            return False

        self.update_serial()
        self.checkConsole()

        command = '\r\nconfig -mode net -wifi "' + self.wifi_ssid + \
            '" "' + self.wifi_pass + '" -token ' + self.token + '\r\n'
        self.serialPort.write(command.encode())
        # TODO verify config success
        return True

    def sdConfig(self):
        self.update_serial()
        self.checkConsole()
        command = '\r\ntime ' + str(int(time.time())) + '\r\n'
        self.serialPort.write(command.encode())
        if len(self.wifi_ssid) == 0:
            self.serialPort.write('config -mode sdcard\r\n'.encode())
        else:
            command = 'config -mode sdcard -wifi "' + \
                self.wifi_ssid + '" "' + self.wifi_pass + '"\r\n'
            self.serialPort.write(command.encode())
        # TODO verify config success
        return True

    def resetConfig(self):
        self.update_serial()
        self.checkConsole()
        self.serialPort.write('\r\nconfig -defaults\r\n'.encode())
        # TODO verify config success
        return True

    def register(self):
        try:
            import secret
            print("Found secrets.py:")
            print("bearer: " + secret.bearer)
            print("Wifi ssid: " + secret.wifi_ssid)
            print("Wifi pass: " + secret.wifi_pass)
            bearer = secret.bearer
            wifi_ssid = secret.wifi_ssid
            wifi_pass = secret.wifi_pass
        except:
            bearer = raw_input("Platform bearer: ")
            wifi_ssid = raw_input("WiFi ssid: ")
            wifi_pass = raw_input("WiFi password: ")
        headers = {'Authorization': 'Bearer ' + bearer,
                   'Content-type': 'application/json;charset=UTF-8', }
        device = {}
        try:
            device['name'] = self.platform_name
        except:
            self.err_out('Your device needs a name!')
            sys.exit()

        device['device_token'] = binascii.b2a_hex(
            os.urandom(3)).decode('utf-8')
        self.token = device['device_token']
        device['description'] = ''
        device['latitude'] = options.latitude
        device['longitude'] = options.longitude
        device['exposure'] = options.exposure
        device['user_tags'] = options.user_tags
        device['is_test'] = str(self.is_test)
        device['postprocessing_attributes']={'meta': self.postprocessing_meta}

        device_json = json.dumps(device)

        backed_device = requests.post('https://api.smartcitizen.me/v0/devices', data = device_json, headers = headers)
        self.id = str(backed_device.json()['id'])
        self.platform_url = "https://smartcitizen.me/kits/" + self.id
        self.serialPort.write(('\r\nconfig -mode net -wifi "' + wifi_ssid +
                               '" "' + wifi_pass + '" -token ' + self.token + '\r\n').encode())
        time.sleep(1)
