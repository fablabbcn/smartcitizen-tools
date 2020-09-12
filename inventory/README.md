# Stock management

A simple command line util to manage stock in yaml files.

`
./stock.py -h
USAGE:

stock.py [options] action[s]

options: -v: verbose
actions: order, delivery
order options: -id order-id -p path -e export
        order -id <oid> -p <path> loads an order and inputs it into the inventory
        order -id <oid> -e <path> loads current inventory status and outputs the necessary order
delivery options: -id delivery-id -p path
`

Can have `orders` (things that you order) and `deliveries` (things that you send). They are managed by simple yaml files.

The components are categorised in `parts` or individual components and `packs` or groups of parts.
The information about the current stock is stored in `parts.yaml`, while the `packs.yaml` file only describes how each pack is made.

Finally, `deliveries` and `orders` have associated status. In the case of the `delivery`: `planned`, `delivered`. In the case of the `order`: `pending`, `placed`, `received`.

## Examples

Create a delivery for a client with `parts` only:

**example_delivery.yaml**

```parts:
  batt_2000mAh: 
    qty: 20
  sck_21:
    qty: 10
packs: null
status: 'pending'
```

```
python stock.py -v delivery -id lovelyclient -p example_delivery.yaml
```

Create a report with the necessary orders to do:

```
python stock.py -v order -id sept2020 -e
```

Input ordered parts:

**orders/amazing_order.yaml**

```
parts:
  ac_cable_3m: 30
status: ordered
```

```
python stock.py -v order -id SEPT2020 -p orders/amazing_order.yaml
```

Input received parts:

**orders/amazing_received_order.yaml**

```
parts:
  ac_cable_3m: 30
status: received
```

```
python stock.py -v order -id SEPT2020 -p orders/amazing_received_order.yaml
```