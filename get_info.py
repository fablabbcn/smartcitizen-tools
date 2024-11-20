import sck
import sys
import os

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

def oneLine(msg):
    enablePrint()
    sys.stdout.write(msg)
    sys.stdout.flush()
    if not verbose: blockPrint()

def enablePrint():
    sys.stdout = sys.__stdout__

blockPrint()
kit = sck.sck()
kit.begin()
kit.getSensors()
kit.getVersion()
kit.getNetInfo()
enablePrint()

if '--mac' in sys.argv: print(kit.esp_macAddress)
if '--sam' in sys.argv: print(kit.sam_firmVer)
if '--esp' in sys.argv: print(kit.esp_firmVer)
