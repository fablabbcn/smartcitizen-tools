import yaml
import sys, os
import datetime

class Delivery():
    def __init__(self, oid):

        self.id = oid

        with open(os.path.join(os.path.dirname(__file__), 'parts.yaml'), 'r') as p:
            self.cparts = yaml.load(p, Loader = yaml.SafeLoader)
        with open(os.path.join(os.path.dirname(__file__), 'packs.yaml'), 'r') as p:
            self.cpacks = yaml.load(p, Loader = yaml.SafeLoader)        
        
        self.packs = None
        self.parts = None
        self.status = None # planned, delivered

        self.changed_cparts = dict()
    
    @property   
    def __getstatus__(self):
        return self.status

    def __setstatus__(self, status):
        self.status = status        

    def load(self, path):
        with open (os.path.join(os.path.dirname(__file__), path), 'r') as file:
            ld = yaml.load(file, Loader = yaml.SafeLoader)

        # Load and unpack
        if 'packs' in ld: self.packs = ld['packs']
        if 'parts' in ld: self.parts = ld['parts']
        if 'status' in ld: self.status = ld['status']

    def save_delivery(self):

        with open (os.path.join(os.path.dirname(__file__), 'deliveries', 'deliveries.yaml'), 'r') as dfile:
            dhist = yaml.load(dfile, Loader = yaml.SafeLoader)

        # Join everything and save
        storage_obj = {'packs': self.packs, 'parts': self.parts, 'status': self.status, 'date': datetime.datetime.today().strftime('%Y%m%d')}
        
        if dhist is None: dhist = dict()
        storage_name = self.id
        while True:
            if storage_name in dhist.keys():
                what_to_do = input (f"Current delivery id [{self.id}] is in delivery history. Input a different name or 'date' to make {self.id}_{datetime.datetime.today().strftime('%Y%m%d')} ")
                if what_to_do == 'date':
                    storage_name = self.id + '_' + datetime.datetime.today().strftime('%Y%m%d')
                else:
                    storage_name = what_to_do
            else:
                break
        print (f'Storing delivery as: {storage_name}')
        dhist[storage_name] = storage_obj

        with open (os.path.join(os.path.dirname(__file__), 'deliveries', f'{storage_name}_archived.yaml'), 'w') as file:
            yaml.dump(storage_obj, file)

        with open (os.path.join(os.path.dirname(__file__), 'deliveries', 'deliveries.yaml'), 'w') as file:
            yaml.dump(dhist, file)            

    def save_parts(self):
        with open (os.path.join(os.path.dirname(__file__), f'parts.yaml'), 'w') as file:
            yaml.dump(self.cparts, file)

    def save_all(self):
        self.save_delivery()
        self.save_parts()

    def check_each(self):
        if self.packs is not None:
            print (self.packs)
            for pack in self.packs:
                print (pack)
                self.check_pack(pack, self.packs[pack])
        if self.parts is not None:
            for part in self.parts:
                self.check_part(part, self.parts[part])

    def check_part(self, part, qty):

        # Parts
        if part not in self.cparts: 
            print (f'Component {part} not in stock')
            return False

        if qty > self.cparts[part]['qty']['unused']:
            print (f'Part {part} [desired qty: {qty}]')
            print (f'Current stock:')
            print (f"- Unused: {self.cparts[part]['qty']['unused']}")
            print (f"- Allocated: {self.cparts[part]['qty']['allocated']}")
            print (f"- To order: {self.cparts[part]['qty']['to_order']}")
            print (f"- Ordered: {self.cparts[part]['qty']['ordered']}")

            while True:

                what_to_do = input('Not enough parts in unused stock, want to input the missing ones for order? [y/n] ')

                # Manage response
                if what_to_do not in ['y', 'n']: what_to_do = input('Please, input y or n. Not enough parts in unused stock, want to input the missing ones for order? [y/n] ')
                if what_to_do == 'y': 
                    self.cparts[part]['qty']['to_order'] += qty - self.cparts[part]['qty']['unused']
                    self.cparts[part]['qty']['allocated'] += self.cparts[part]['qty']['unused']
                    self.cparts[part]['qty']['unused'] = 0
                    print (f"part {part} placed to order [{qty - self.cparts[part]['qty']['unused']}]. Allocating [{self.cparts[part]['qty']['unused']}]")
                    if part not in self.changed_cparts: 
                        self.changed_cparts[part] = dict()
                        self.changed_cparts[part]['amount-alloc'] = 0
                        self.changed_cparts[part]['amount-order'] = 0
                    self.changed_cparts[part]['what'] = 'allocate-order'
                    self.changed_cparts[part]['amount-alloc'] += self.cparts[part]['qty']['unused']
                    self.changed_cparts[part]['amount-order'] += qty - self.cparts[part]['qty']['unused']
                    break
                # Insist if no
                else:
                    if self.cparts[part]['qty']['unused'] > 0:
                        double_check = True
                        
                        while double_check:
                            what_to_do = input(f"Should I allocate at least the unused parts [{self.cparts[part]['qty']['unused']}]? [y/n] ")

                            if what_to_do not in ['y', 'n']: what_to_do = input(f"Please, input y or n. Should I allocate at least the unused parts [{self.cparts[part]['qty']['unused']}]? [y/n] ")
                            if what_to_do == 'y':
                                self.cparts[part]['qty']['allocated'] += self.cparts[part]['qty']['unused']
                                self.cparts[part]['qty']['unused'] = 0

                                if part not in self.changed_cparts: 
                                    self.changed_cparts[part] = dict()
                                    self.changed_cparts[part]['amount'] = 0
                                self.changed_cparts[part]['what'] = 'allocate'
                                self.changed_cparts[part]['amount'] += self.cparts[part]['qty']['unused']
                                
                                double_check = False
                            if what_to_do == 'n': 
                                double_check = False

                    break
        else:
            self.cparts[part]['qty']['unused'] -= qty
            self.cparts[part]['qty']['allocated'] += qty
            if part not in self.changed_cparts: self.changed_cparts[part] = dict()
            self.changed_cparts[part]['what'] = 'allocate'
            self.changed_cparts[part]['amount'] = qty            

    def check_pack(self, pack, qty):

        # Components
        for part in self.cpacks[pack]['parts']:
            if part not in self.cparts: 
                print (f'part {part} not in stock')

                return False

            # Desired quantity
            dqty = self.cpacks[pack]['parts'][part] * qty

            self.check_part(part, dqty)

    def out_summary(self):
        print ('--------')
        print ('Summary:')
        for Part in self.changed_cparts:
            print (f'Part {Part}')
            print (f"- Updated Stock: {self.cparts[Part]['qty']['unused']}")
            print (f"- Updated Orders: {self.cparts[Part]['qty']['to_order']}")
            if self.changed_cparts[Part]['what'] == 'allocate':
                print (f"- Increased allocation by: {self.changed_cparts[Part]['amount']}")
            if self.changed_cparts[Part]['what'] == 'allocate-order':
                print (f"- Increased allocation by: {self.changed_cparts[Part]['amount-alloc']}\n- Increased order amount by: {self.changed_cparts[Part]['amount-order']}")
        print ('--------')


class Order():
    def __init__(self, oid):
        self.id = oid

        with open(os.path.join(os.path.dirname(__file__), 'parts.yaml'), 'r') as p:
            self.cparts = yaml.load(p, Loader = yaml.SafeLoader)
        with open(os.path.join(os.path.dirname(__file__), 'packs.yaml'), 'r') as p:
            self.cpacks = yaml.load(p, Loader = yaml.SafeLoader)        
        
        self.packs = dict()
        self.parts = dict()
        self.status = None # pending, placed, received

        self.to_order = dict()
        self.to_order['parts'] = dict()
        self.to_order['status'] = None

    def export(self):

        for part in self.cparts:
            if self.cparts[part]['qty']['to_order'] is not None:
                if self.cparts[part]['qty']['to_order'] > 0: self.to_order['parts'][part] = self.cparts[part]['qty']['to_order']

        if self.to_order['parts']:
            print ('--------')
            print ('Summary:')
            for part in self.to_order['parts']: print (f"Part {part} to order: {self.to_order['parts'][part]}")
            print ('--------')


            what_to_do = input(f'Want to mark the parts as ordered? ')
            while True:
                if what_to_do not in ['y', 'n']: what_to_do = input(f'Please input y or n. Want to mark the parts to order? ')
                else: break
            if what_to_do == 'y': 
                self.to_order['status'] = 'pending'
                for part in self.cparts:
                    if self.cparts[part]['qty']['to_order'] is not None:
                        if self.cparts[part]['qty']['to_order'] > 0: 
                            self.cparts[part]['qty']['ordered'] = self.cparts[part]['qty']['to_order'] + self.cparts[part]['qty']['ordered']
                            self.cparts[part]['qty']['to_order'] = 0

            self.save_parts()

            what_to_do = input(f'Want to export the order file? ')
            while True:
                if what_to_do not in ['y', 'n']: what_to_do = input(f'Please input y or n. Want to export the order file? ')
                else: break
            
            if what_to_do == 'y': 
                what_to_do = input(f'Format (csv/yaml)? ')
                while True:
                    if what_to_do not in ['csv', 'yaml']: what_to_do = input(f'Format (csv/yaml)? ')
                    else: break
                date = datetime.datetime.today().strftime('%Y%m%d')
                filename = f'{date}_{self.id}_orders.{what_to_do}'
                print (f'Saving as {filename}')
                if what_to_do == 'yaml':    
                    with open(os.path.join(os.path.dirname(__file__), 'orders', filename), 'w') as o:
                        yaml.dump(self.to_order, o)
                elif what_to_do == 'csv':
                    csvFile = open(os.path.join(os.path.dirname(__file__), 'orders', filename), 'w')
                    csvFile.write("Qty,Description,Distributor, Mfr. Reference,Dtr. Reference,Info URL,Dtr. URL\n")
                    for part in self.to_order['parts']:
                        qty = self.to_order['parts'][part]
                        description = self.cparts[part]['description']
                        distributor = self.cparts[part]['distributor']
                        mfrref = self.cparts[part]['manufacturer_ref']
                        dtrref = self.cparts[part]['distributor_ref']
                        infourl = self.cparts[part]['info_url']
                        dtrurl = self.cparts[part]['distributor_url']
                        csvFile.write(f"{qty},{description},{distributor},{mfrref},{dtrref},{infourl},{dtrurl}\n")
                    csvFile.close()
        else:
            print ('No parts to order currently')

    def save_parts(self):
        with open (os.path.join(os.path.dirname(__file__), f'parts.yaml'), 'w') as file:
            yaml.dump(self.cparts, file)

    def load(self, path):
        # Load and unpack
        with open (os.path.join(os.path.dirname(__file__), path), 'r') as file:
            lo = yaml.load(file, Loader = yaml.SafeLoader)

        flag = True
        if 'parts' in lo: self.parts = lo['parts']; flag &= False
        if 'packs' in lo: self.packs = lo['packs']; flag &= False
        if flag: return
        
        if self.packs:
            for pack in self.packs:
                if pack not in self.cpacks:
                    print (f'Pack in order [{pack}] not in packs.yaml')
                else:
                    for part in self.cpacks[pack]['parts']:
                        # How many parts does that pack have
                        packqty = self.cpacks[pack]['parts'][part]['qty']
                        partqty = packqty * self.packs[pack]

                        if part not in self.parts:
                            self.parts[part] = partqty
                        else:
                            self.parts[part] += partqty

        if 'status' in lo:
            if lo['status'] == 'placed':
                print ('Ordered parts')
                for part in self.parts:
                    if part in self.cparts:
                        print ('-------')
                        
                        self.cparts[part]['qty']['ordered'] += self.parts[part]
                        self.cparts[part]['qty']['to_order'] -= self.parts[part]
                        if self.cparts[part]['qty']['to_order'] < 0: self.cparts[part]['qty']['to_order'] = 0
                        print (f'{part} ordered: {self.parts[part]}')
            
            if lo['status'] == 'pending':
                print ('Parts to order')
                for part in self.parts:
                    if part in self.cparts:
                        print ('-------')
                        
                        self.cparts[part]['qty']['to_order'] = self.parts[part]
                        print (f'{part} to order: {self.parts[part]}')

            if lo['status'] == 'received':
                print ('Received parts')
                for part in self.parts:
                    if part in self.cparts:
                        print ('-------')
                        
                        self.cparts[part]['qty']['ordered'] -= self.parts[part]
                        if self.cparts[part]['qty']['ordered'] < 0: self.cparts[part]['qty']['ordered'] = 0
                        self.cparts[part]['qty']['unused'] += self.parts[part]
                        print (f'{part} received: {self.parts[part]}')

        else: return

        what_to_do = input('Want to save parts into parts.yaml? ')
        while True:
            if what_to_do not in ['y', 'n']: what_to_do = input('Please, input y or n, Want to save parts into parts.yaml? ')
            else: break
        if what_to_do == 'y': self.save_parts()

if '-h' in sys.argv or '--help' in sys.argv or '-help' in sys.argv:
    print('USAGE:\n\nstock.py [options] action[s]')
    print('\noptions: -v: verbose')
    print('actions: order, delivery')
    print('order options: -id order-id -p path -e export')
    print('\torder -id <oid> -p <path> loads an order and inputs it into the inventory')
    print('\torder -id <oid> -e <path> loads current inventory status and outputs the necessary order')
    print('delivery options: -id delivery-id -p path')
    sys.exit()

# Print management
def blockPrint():
    sys.stdout = open(os.devnull, 'w')
def enablePrint():
    sys.stdout = sys.__stdout__

blockPrint()
if '-v' in sys.argv: 
    enablePrint()

# Order
if 'order' in sys.argv:
    if '-id' not in sys.argv: print ('ID required'); sys.exit()
    if '-id' in sys.argv: did = sys.argv[sys.argv.index('-id')+1]   

    order = Order(did)
    if '-e' in sys.argv: order.export(); sys.exit()

    if '-p' in sys.argv: 
        path = sys.argv[sys.argv.index('-p')+1]
        order.load(path)
        sys.exit()

    print ('At least a path or an export option is required for orders')
    sys.exit()

# Delivery
if 'delivery' in sys.argv:
    if '-id' not in sys.argv: print ('ID required'); sys.exit()
    if '-p' not in sys.argv: print ('Path required'); sys.exit()

    if '-id' in sys.argv: did = sys.argv[sys.argv.index('-id')+1]
    if '-p' in sys.argv: path = sys.argv[sys.argv.index('-p')+1]

    # Make delivery
    delivery = Delivery(did)
    delivery.load(path)
    delivery.check_each()

    delivery.out_summary()
    what_to_do = input('Want to store delivery? [y/n] ')
    while True:
        # Manage response
        if what_to_do not in ['y', 'n']: what_to_do = input('Please, input y or n. Want to store delivery? [y/n] ')
        else: break
    if what_to_do == 'y': delivery.save_delivery(); delivery.status = "planned"
    if what_to_do == 'n': sys.exit();

    if what_to_do == 'y':
        what_to_do = input('Want to store parts status? [y/n] ') 
        while True:
            # Manage response
            if what_to_do not in ['y', 'n']: what_to_do = input('Please, input y or n. Want to store parts status? [y/n]')
            else: break
        if what_to_do == 'y': delivery.save_parts()
        sys.exit()

print ('At least an action is required (order/delivery)')