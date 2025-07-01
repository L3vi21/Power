import struct
import csv
import time
from pathlib import Path
import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import schedule
import threading
from concurrent.futures import ThreadPoolExecutor

#Number of samples taken per meter
num_samples= 5
#Delay in seconds between each data read
sample_delay= 60

#Finds the parent file path
script_dir = Path(__file__).parent
csv_path = script_dir / "ips.csv"
#Path to the DentInstruments register list
excel_path = script_dir / 'PSHD_MASTER_REGISTER_LIST_current-4.xlsx'
sheet_name = "A"

#Synchronization variable
csv_lock = threading.Lock()

#Takes the string of register names and creates a list of int versions of them
def register_parser(registers_str):
    return[int(reg.strip()) for reg in registers_str.split(',') if reg.strip()]

#Creates necessary csv file if DNE, and appends any necessary data or headers to file
def append_to_csv(filename, data, header):
    with csv_lock:
        file_exists= Path(filename).exists()
        write_header= not file_exists
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists and write_header:
                writer.writerow(header)
            writer.writerow(data)

def process_device(row, register_name_map):
    ip = row['ip'].strip()
    slave= row['slave'].strip()
    description = row['description'].strip()
    registers = register_parser(row['start_addr'])
    
    # Convert slave to integer
    slave_id= int(slave)

    #Connect to Modbus, No need for slave ID, just keep it constant at 1 per default value
    client = ModbusClient(host=ip, port=502, unit_id=1, auto_open=True, timeout=3.0)

    try:
        print(f"\nReading from {description} ({ip}, slave {slave_id})")
        client.open()
        print("Client open:", client.is_open)

        for _ in range(num_samples):
            for reg_start in registers:
                reg_name = register_name_map.get(reg_start, f"Register{reg_start}")
                print(f"Attempting to read from register {reg_name} (Reg_value={reg_start})")

                regs= client.read_holding_registers(reg_start-1, 2)

                if regs and len(regs) == 2:
                    try:
                        float_value = struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]
                        time_of_data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        print(f"Decode error: {str(e)}")
                        continue

                    safe_reg_name = reg_name.replace(" ", "_").replace("/", "-")
                    data_row = [time_of_data, description, ip, slave_id, reg_start, reg_name, float_value]
                    header = ["Timestamp", "Description", "IP", "Slave", "Register", "Register_Name", "Value"]
                    append_to_csv(f"metered_data_{safe_reg_name}.csv", data_row, header)
                else:
                    print(f"Read Failed for {reg_name} ({reg_start})")
                    error_path = script_dir / "errors.csv"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    append_to_csv(error_path, [timestamp, ip, reg_start, "Read Failed"], ["Timestamp", "IP", "Register", "Error"])
            time.sleep(sample_delay)
    finally:
        client.close()


def pull_data():
    # Reads specified columns of the excel sheet, specifically the register name
    df = pd.read_excel(excel_path, sheet_name= sheet_name, skiprows= 7, header= 0, usecols = ['Modbus Register Name', 'Modbus\n Register'], engine= 'openpyxl')
    # Removes any missing values
    df = df.dropna(subset = ['Modbus Register Name', 'Modbus\n Register'])

    #Builds the map of all the register names
    register_name_map = {}
    for _, row in df.iterrows():
        reg_value= row['Modbus\n Register']
        register_name_map[reg_value] = row['Modbus Register Name']
    
    with open(csv_path, 'r') as csv_file:
        devices= list(csv.DictReader(csv_file))

    num_devices = len(devices)
    max_workers = min(num_devices, 32) if num_devices > 0 else 1

    # Change the max_workers to the number of devices you want to read from concurrently
    # This is set to 21 because there are 21 devices in the csv file
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for row in devices:
            executor.submit(process_device, row, register_name_map)

# Schedules the data pulling for every 10 minutes
schedule.every(2).minutes.do(pull_data)

while True:
    schedule.run_pending()
    time.sleep(1)