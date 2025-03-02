import serial
import serial.tools.list_ports
import time
import sys
from os import name
# Check if we are in windows
_mswin = name == 'nt'

try:
    from serialtools.serialworker import serialworker
except ModuleNotFoundError:
    try:
        from src.tools.serialtools.serialworker import serialworker
    except:
        print ('Cannot import serialworker. Check library dependencies')
    pass

class serialdevice:

    def __init__(self, device_type = None, verbose = 2):
        # Serial port
        self.serialPort = None
        self.serialPort_name = None
        self.serialNumber = None
        self.worker = None
        self.verbose = 2     # 0 -> never print anything, 1 -> print only errors, 2 -> print everything
        self.type = device_type

    def set_serial(self, port=None, force=False):
        device_list = list(serial.tools.list_ports.comports())
        number_devices = len(device_list)
        if number_devices == 0:
            self.err_out('No device found')
            return False

        if port is not None:
            if not any([port == d.device for d in device_list]):
                self.err_out(f'Port: {port} not found')
                return False

        if self.type == 'sck':
            kit_list = []
            for d in device_list:
                try:
                    if 'Smartcitizen' in d.description:
                        self.std_out('['+str(device_list.index(d))+'] Smartcitizen Kit S/N: ' + d.serial_number)
                        kit_list.append(d)
                    # TODO Hack for windows as the SCK doesn't show up as Smartcitizen
                    elif _mswin:
                        if 'Arduino' in d.description:
                            self.std_out('['+str(device_list.index(d))+'] Smartcitizen Kit S/N: ' + d.serial_number)
                            kit_list.append(d)
                except:
                    pass

            if port is not None:
                if not force:
                    if not any([port in d.device for d in kit_list]):
                        self.err_out(f'SCK not found in port: {port}')
                        return False
                for d in device_list:
                    if port == d.device:
                        self.serialPort_name = d.device
                        self.serialNumber = d.serial_number
                        return True
                self.err_out(f'Port: {port} not found')
                return False

            number_devices = len(kit_list)
            device_list = kit_list

            if number_devices == 0:
                self.err_out('No SCK found')
                return False

        if number_devices == 1:
            which_device = 0
        else:
            for d in device_list: self.std_out(str(device_list.index(d) + 1) + ' --- ' + d.device)
            which_device = int(input('Multiple devices found, please select one: ')) - 1

        self.serialPort_name = device_list[which_device].device
        self.serialNumber = device_list[which_device].serial_number
        return True

    def update_serial(self, speed = 115200, timeout_ser=0.5):
        # Find serial number and assign serial port name
        timeout = time.time() + 15
        while True:
            devList = list(serial.tools.list_ports.comports())
            found = False
            for d in devList:
                try:
                    if self.serialNumber in d.serial_number:
                        self.serialPort_name = d.device
                        found = True
                    if time.time() > timeout:
                        self.err_out('Timeout waiting for device')
                        sys.exit()
                except:
                    pass
            if found: break

        # Open port
        timeout = time.time() + 15
        time.sleep(0.1)
        while self.serialPort is None:
            try:
                time.sleep(0.1)
                self.serialPort = serial.Serial(self.serialPort_name, speed, timeout = timeout_ser)
            except:
                if time.time() > timeout:
                    self.err_out('Timeout waiting for serial port')
                    sys.exit()
            time.sleep(0.1)

        if self.type == 'sck':
            # Open the port
            while True:
                try:
                    if self.serialPort.write("\r\n".encode()): return
                except OSError:
                    self.serialPort = serial.Serial(self.serialPort_name, speed, timeout = timeout_ser)
                    continue
                break

    def read_all_serial(self, chunk_size=200):
        """Read all characters on the serial port and return them"""
        if not self.serialPort.timeout:
            raise TypeError('Port needs to have a timeout set!')

        read_buffer = b''

        while True:

            byte_chunk = self.serialPort.read(size=chunk_size)
            read_buffer += byte_chunk
            if not len(byte_chunk) == chunk_size:
                break

        return read_buffer

    def flush(self):
        self.serialPort.reset_input_buffer()

    def start_streaming(self, buffer_length = 10, raster = 0.2, columns = []):
        '''
            buffer_length: Number of samples to buffer before putting into the queue
            raster = sampling period
        '''
        # try:
        #     import pandas as pd

        # except ModuleNotFoundError:
        #     self.err_out ('Cannot import pandas module. Streaming is not be available')
        #     return
        # else:
        #     if df is None:
        #         pd.DataFrame({'Time': [], 'y': []}, columns = ['Time', 'y'])

        self.worker = serialworker(self, buffer_length, raster, columns)
        self.worker.daemon = True
        self.worker.start()

    def read_line(self):
        return self.serialPort.readline().decode('utf-8').strip('\r\n').split('\t')

    def end(self):
        if self.serialPort.is_open: self.serialPort.close()

    def std_out(self, msg):
        if self.verbose >= 2: print(msg)

    def err_out(self, msg):
        if self.verbose >= 1:
            sys.stdout.write("\033[1;31m")
            print('ERROR ' + msg)
            sys.stdout.write("\033[0;0m")