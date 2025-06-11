import csv
from pathlib import Path
from pyModbusTCP.client import ModbusClient

script_dir = Path(__file__).parent
csv_path = script_dir / "ips.csv"

def register_parser(registers_str):
    return[int(reg.strip()) for reg in registers_str.split(',') if reg.strip()]

#print(register_parser("41200, 42345, 41176, 42337, 41168, 42333, 41192"))
#Output: [41200, 42345, 41176, 42337, 41168, 42333, 41192]

with open(csv_path, 'r') as csv_file:
    reader = csv.DictReader(csv_file)

    for row in reader:
        ip = row['ip'].strip()
        slave = row['slave'].strip()
        description = row['description'].strip()
        count = int(row['count'].strip())
        registers = register_parser(row['start_addr'])

        #If slave does not exist
        if not slave:
            continue

        slave_id = int(slave)

        #Connect to Modbus
        client = ModbusClient(host=ip, port=502, unit_id=slave_id, auto_open=True)

        #Ensures correct connection to the modbus to the specific meter
        print(f"\nReading from {description} ({ip}, slave {slave_id})")
        client.open()
        print("Client open:", client.is_open)

        for reg_start in registers:
            print(f"Attempting to read from register {reg_start} (count={count})")
            regs = client.read_holding_registers(reg_start, count)
            print(f"Read result for {reg_start}: {regs}")

            if regs:
                print(f"  Registers {reg_start} - {reg_start+count-1}: {regs}")




