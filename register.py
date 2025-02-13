#!/usr/bin/python

from traceback import print_exc
import sys, time, os
import shutil
import options

sys.path.append("./tools")

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

def oneLine(msg):
    enablePrint()
    sys.stdout.write(msg)
    sys.stdout.flush()
    if not verbose: blockPrint()

def enablePrint():
    sys.stdout = sys.__stdout__

if '-h' in sys.argv or '--help' in sys.argv or '-help' in sys.argv:
    print('USAGE:\n\nresgister.py [options] action[s]')
    print('\noptions: -v: verbose; -t: test device')
    print('actions: register, inventory')
    print('register options: -n platform_name')
    print('inventory -d "description" --with-test [y/n] (default: n)')
    print('-p port [-f]: specify a port instead of scanning')
    print('-f: option ignores serial device description (must contain Smartcitizen otherwise)')
    print('--dry-run: do not register, simply check how it would look')
    print('--tokenize-name token: remove spaces from name and add token character')
    print('--sleep: send kit to sleep after registering (1s after)')
    sys.exit()

import sck
kit = sck.sck(check_pio = False)

force = False
port = None
if '-p' in sys.argv:
    port = sys.argv[sys.argv.index('-p')+1]
    if '-f' in sys.argv: force = True
elif '-f' in sys.argv: ERROR('No force action if port is not specified'); sys.exit()
if not kit.begin(port=port, force=force): sys.exit()

verbose = False
blockPrint()
if '-v' in sys.argv:
    verbose = True
    enablePrint()

if 'register' in sys.argv:
    kit.getNetInfo()
    kit.getVersion()

    if '-n' not in sys.argv:
        kit.platform_name = 'Test #'
    else:
        kit.platform_name = sys.argv[sys.argv.index('-n')+1] + ' #'

    if '-t' in sys.argv or '--test':
        print ('Setting test device')
        kit.is_test = True

    if kit.is_test and not options.test_meta:
        print ('Need to specify test type in options')
        sys.exit()

    try:
        kit.platform_name = options.test_meta['id'] + ' ' + kit.platform_name
        kit.postprocessing_meta = f"{options.test_meta['type']}-{options.test_meta['id']}-{options.test_meta['batch']}".lower()
    except KeyError:
        print ('Review test options')
        sys.exit()

    if options.mac:
        kit.platform_name = kit.platform_name + kit.esp_macAddress[-5:].replace(':', '')

    if '--tokenize-name' in sys.argv:
        token_char = sys.argv[sys.argv.index('--tokenize-name')+1]
        print (f'Tokenizing name with: \"{token_char}\"')
        kit.platform_name = kit.platform_name.replace(' ', token_char)

    if '--dry-run' not in sys.argv:
        kit.register()

    enablePrint()
    print("\r\nSerial number: " + kit.sam_serialNum)
    print("Mac address: " + kit.esp_macAddress)
    print("Device token: " + kit.token)
    print("Platform kit name: " + kit.platform_name)
    if '--dry-run' not in sys.argv:
        print("Platform page: " + kit.platform_url)
        if kit.postprocessing_meta is not None:
            print("Postprocessing['meta']: " + kit.postprocessing_meta)

    if '--sleep' in sys.argv:
        time.sleep(1)
        kit.sleep()

if 'inventory' in sys.argv:
    inventory_path = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'inventory')

    print (f'Using inventory in: {inventory_path}')
    if '-d' in sys.argv:
        kit.description = sys.argv[sys.argv.index('-d')+1]
    else:
        kit.description = ''
    kit.getNetInfo()
    kit.getVersion()

    if '--with-test' in sys.argv:
        tested = 'y'
    else:
        tested = 'n'

    if not hasattr(kit, 'token'):
        kit.token = ''
    if not hasattr(kit, 'platform_name'):
        kit.platform_name = ''
    if not hasattr(kit, 'platform_url'):
        kit.platform_url = ''

    local_inv_name = "inventory.csv"
    if not os.path.exists(inventory_path): os.makedirs(inventory_path)

    if os.path.exists(os.path.join(inventory_path, local_inv_name)):
        shutil.copyfile(os.path.join(inventory_path, local_inv_name), inventory_path+".BAK")
        csvFile = open(os.path.join(inventory_path, local_inv_name), "a")
    else:
        csvFile = open(os.path.join(inventory_path, local_inv_name), "w")
        csvFile.write("time,serial,mac,sam_firmVer,esp_firmVer,description,token,platform_name,platform_url,tested,validated,min_validation_date,max_validation_date,replacement,test,destination,batch\n")
    pass

    print (f'Writing into file for Kit: {kit.esp_macAddress}')
    csvFile.write(time.strftime("%Y-%m-%dT%H:%M:%SZ,", time.gmtime()))
    csvFile.write(kit.sam_serialNum + ',' + kit.esp_macAddress + ',' + kit.sam_firmVer + ',' + kit.esp_firmVer + ',' + kit.description + ',' + kit.token + ',' + kit.platform_name + ',' + kit.platform_url + ',' + tested + ',' + ',' + ',' +',' + ',' +',' + ',' +'\n')
    csvFile.close()
