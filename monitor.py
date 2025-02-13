import sys
# sys.path.append("./tools")
from sck import sck

if __name__ == '__main__':

    print ('Opening kit')
    kit = sck(check_pio=True)
    kit.begin(port="/dev/ttyACM0")

    print ('Getting sensors')
    kit.getSensors()
    print (kit.sensor_enabled)

    kit.monitor(sensors=['Temperature', 'Humidity', 'Noise dBA'])

    print ('Getting the worker output')
    while True:
        data = kit.worker.output.get()
        print (data[0])
        print (data[1])

        # Do whatever with the data






