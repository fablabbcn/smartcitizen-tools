#!/usr/bin/python

from os.path import join, dirname
from os import walk
import sys
import pandas as pd


if '-h' in sys.argv or '--help' in sys.argv:
    print ('Help:')
    print ('Supplier parts file in parts folder')
    print ('--purchase-order -p: file for purchase order')
    sys.exit()

if '--purchase-order' in sys.argv or '-p' in sys.argv:
    if '-p' in sys.argv:
        po_file = sys.argv[sys.argv.index('-p')+1]
    else:
        po_file = sys.argv[sys.argv.index('--purchase-order')+1]
else:
    print ('Need sales input file')
    sys.exit()

suppliers_folders = join(dirname(__file__), 'supplier')

supplier_files = []
for root, dirs, files in walk(suppliers_folders):
        for file in files:
            if file.endswith(".csv"):
                supplier_files.append(file)

if supplier_files:
    if len(supplier_files)>1:
        for pf in supplier_files: 
            print (str(supplier_files.index(pf) + 1) + ' --- ' + pf)   
        which_file = input('Select Supplier Part file: ')
    else:
        which_file = 1

    supplier_file = supplier_files[int(which_file) - 1]
else:
    print (f'No Supplier Part files (.csv) found in {suppliers_folders}')
    sys.exit()

sp_df = pd.read_csv(join(suppliers_folders, supplier_file))
po_df = pd.read_csv(po_file)

# Prepare sp_df
sp_df.set_index('SKU', inplace=True)
sp_df.drop(['supplier', 'id', 'part', 'part_name', 'manufacturer', 
            'note', 'base_cost', 'MPN', 'packaging', 'multiple'], axis = 1, inplace=True)

# Prepare po_df
po_df.set_index('SKU', inplace=True)
po_df.drop(['purchase_price_currency', 'purchase_price', 'part', 
            'notes', 'reference'], axis = 1, inplace=True)

# Merged
merged = pd.merge(sp_df, po_df, left_index=True, right_on='SKU').reset_index()
merged['info'] = ''
merged['requester'] = ''
merged.set_index('quantity', inplace=True)

output = merged.reindex(columns= ['part_name', 'supplier_name', 'MPN', 'SKU', 'info', 'link', 'requester'])

print (output)
output.to_csv(join(dirname(__file__),'output_po.csv'))