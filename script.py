import struct
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from pyModbusTCP.client import ModbusClient

script_dir = Path(__file__).parent
csv_path = script_dir / "ips.csv"
output_csv = script_dir / "modbus_data.csv"
excel_path = script_dir / 'PSHD_MASTER_REGISTER_LIST_current-4.xlsx'
sheet_name = "A"

#Takes the string of register names and creates a list of int versions of them
def register_parser(registers_str):
    return[int(reg.strip()) for reg in registers_str.split(',') if reg.strip()]

#Creates necessary csv file if DNE, and appends any necessary data or headers to file
def append_to_csv(filename, data, header):
    file_exists = Path(filename).exists()

    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists and header:
            writer.writerow(header)
        writer.writerow(data)

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
        
        #Converts slave id to useable int
        slave_id = int(slave)

        #Connect to Modbus, No need for slave ID, just keep it constant at 1 per default value
        client = ModbusClient(host=ip, port=502, unit_id=1, auto_open=True, timeout=3.0)

        #Ensures correct connection to the modbus to the specific meter
        print(f"\nReading from {description} ({ip}, slave {slave_id})")
        client.open()
        print("Client open:", client.is_open)

        #Example of accessing the frequency register, is able to get the proper registers
        #Able to convert the data and store it as a float into a csv file with a proper header as well

        #regs = client.read_holding_registers(1165-1,2)

        #if regs and len(regs) == 2:
        #    float_value = struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]
        #    print("Dent Instruments float value:", float_value)
        #    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #    data_row = [timestamp, description, ip, slave_id, 1165, float_value]
        #    header = ["Timestamp", "Description", "IP", "Slave", "Register", "Value"]
        #    append_to_csv(output_csv, data_row, header)

        #Accessing multiple registers and store them into their own csv files top then be able to graph


        for reg_start in registers:
            print(f"Attempting to read from register {reg_start} (count={count})")
            regs = client.read_holding_registers(reg_start-1, 2)
            
            #Makes sure that the data being stored is a float32 made up of two 16 bit register
            if regs and len(regs) == 2:
                float_value = struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                df = pd.read_excel(excel_path, sheet_name= sheet_name, skiprows= 6, usecols = ['Modbus Register Name', 'Modbus\n Register'])
                

                data_row = [timestamp, description, ip, slave_id, 1165, float_value]
                header = ["Timestamp", "Description", "IP", "Slave", "Register", "Value"]
                append_to_csv("metered_data_" + str(), data_row, header)
            else:    
                print("Read Failed")





