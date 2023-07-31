#!/usr/bin/python
import sys
import subprocess
import serial
from serial.tools import list_ports
import time
import datetime
import os
import shutil
import sck
import json

class sck_monitor():

    state = {}
    confDir = os.path.join(os.getcwd(), 'sck_mon')
    dry_run = False
    old_devices = set()
    logFile = ''
    stateFile = ''
    configFile = ''

    def __init__(self):
        self.logFile = os.path.join(self.confDir, 'sck_mon.log')
        self.stateFile = os.path.join(self.confDir, 'sck_mon.state')
        self.configFile = os.path.join(self.confDir, 'sck_mon.config')
        if not os.path.exists(self.confDir): os.mkdir(self.confDir)
        # self.state['kits'] = {}


    def check_new_devices(self):
        devices = set([item for item in list_ports.comports()])
        added = devices.difference(self.old_devices)
        removed = self.old_devices.difference(devices)
        if len(added):
            for d_added in added: 
                self.log_out (f'Added device: {d_added}', 'INFO')
                if not self.add_new_device(d_added.device):
                    self.log_out(f'Failed creating new device: {d_added}', 'ERROR')
        if len(removed):
            for d_removed in removed: self.log_out (f'Removed device: {d_removed}', 'INFO')
        self.old_devices = devices

    def loop(self):
        while True:
            self.check_new_devices()
            self.check_repo()
            time.sleep(1)

    def log_out(self, msg, kind = 'INFO'):
        log_line = f'{datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")} [{kind}]: {msg}\n'
        print(log_line, end='')
        with open (self.logFile, 'a') as file:
             file.write(log_line)
 
    def add_new_device(self, port):
        kit = sck.sck(verbose=0)
        if not kit.begin(port=port):
            return False
        while not kit._infoReady:
            kit.getInfo()

        kitID = kit.esp_macAddress[-5:].replace(':', '')

        if kitID in self.state:
            print('Kit is already configured in state file')
            # Reconfiugure kit
            # decidir como manejar esto:
            # Se podría implementar un config en sck.py que se coma un json con toda la configuyracion incluida la de intervalos
            # o hacerla una por una aqui
            savedKit        = self.state[kitID]
            kit.mode        = savedKit['mode']
            kit.token       = savedKit['token']
            kit.wifi_ssid   = savedKit['wifi_ssid']
            kit.wifi_pass   = savedKit['wifi_pass']
            kit.pubInt      = savedKit['pubInt']
            kit.readInt     = savedKit['readInt']
            # kit.config()

        else:
            kitJson = kit.json_obj() # Gets config from kit

            # And adds the rest of the config with default values
            kitJson['commit'] = 'latest'
            kitJson['branch'] = 'master'
            kitJson['platform_id'] = 0
            kitJson['platform_name'] = ''
            kitJson['platform_url'] = 'https://smartcitizen.me/kits/' + str(kitJson['platform_id'])
            self.state[kitID] = kitJson
            self.save_state_file()

        self.log_out(f'Started monitoring kit on: {port}', 'INFO')

        return True

    def load_state_file(self):
        try:
            with open(self.stateFile, "r") as file:
                self.state = json.load(file)
        except:
            with open (self.stateFile, 'w') as file:
                json.dump(self.state, file, indent=4, sort_keys=True)

        ## Poner el valor de readint general (integrarlo en sck.py)
        ## Lo mismo con el pubint


    def save_state_file(self):
        print(self.state)
        with open (self.stateFile, 'w') as file:
            json.dump(self.state, file, indent=4, sort_keys=True)
        self.log_out(f'Saved state file', 'INFO')
        # Trigger this when:
        # a kit that is not in the state file was added
        # a kit is disconnected (only if we want to show if a kit is online/offline)
        # a config change has been executed by modifying the sck_mon.config file.
        pass

    def check_config(self):
        # This function updates config of the kits if the sck_mon.config file is modifyed
        # We can check this file in a regular interval or fins a way to monitor it for changes on the filesystem
        pass

    def check_repo(self):
        # This will check the repo for new commits and reflash the kits if needed
        pass

    def log_serial(self, kit):
        # This will save to a file all the Serial output of the kit
        # We can do this with an external tool like screen or tio, or use python internally
        pass


    def start_logging(devs, configs, log_dir, log):
        for dev in list(devs):
            dlog = None
            for config in configs:
                # Find by serial_number
                if configs[config]['sn'] == dev.serial_number:
                    dlog = os.path.join(log_dir, config, 'monitor.log')
                    # Rename existing log just in case
                    if os.path.exists(dlog):
                        logs = get_logs(os.path.join(log_dir, config))
                        shutil.move(dlog, dlog + f'.{len(logs)}')
                    log_out(f'Started logging on device {dev.device}. Logfile: {dlog}', log, 'INFO')
                    subprocess.call(['screen', '-d', '-m', '-L', '-Logfile', dlog, dev.device])
            if dlog is None:
                log_out(f'Device {dev} not configured (sn: {dev.serial_number})', log, 'WARNING')
        return


if __name__ == '__main__':

    if '-h' in sys.argv or '--help' in sys.argv or '-help' in sys.argv:
        print('sck_monitor: Tool to monitor and manage connected Smartcitizen kits')
        print('\nUSAGE:\n\tsck_monitor.py [options]')
        print('\nOptions:')
        print('\t--conf-dir: Directory with config file and where logs where be stored')
        print('\t--dry-run: dry run')
        sys.exit()

    sck_mon = sck_monitor()
 
    if '--dry-run' in sys.argv: sck_monitor.dry_run = True

    if '--log-dir' in sys.argv:
        sck_mon.confDir = sys.argv[sys.argv.index('--conf-dir')+1]

    sck_mon.load_state_file()
    sck_mon.loop()

# TODO 
# Manage sleep state, if sck_monitor is started when the kit is sleep...
