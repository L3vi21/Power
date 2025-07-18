import struct
import csv
import time
from pathlib import Path
import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import threading
from concurrent.futures import ThreadPoolExecutor

#Finds the parent file path
script_dir = Path(__file__).parent
csv_path = script_dir / "ips.csv"
#Path to the DentInstruments register list
excel_path = script_dir / 'PSHD_MASTER_REGISTER_LIST_current-4.xlsx'
sheet_name = "A"
# Define the directory for saving metered data and ensure it exists
data_dir = script_dir / "metered_data"
data_dir.mkdir(exist_ok=True)

#Synchronization variable
csv_lock = threading.Lock()

#Takes the string of register names and creates a list of int versions of them
def register_parser(registers_str):
    return[int(reg.strip()) for reg in registers_str.split(',') if reg.strip()]

#Creates necessary csv file if DNE, and appends any necessary data or headers to file
def append_to_csv(filename, data, header):
    with csv_lock:
        file_exists= Path(filename).exists()
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)
            writer.writerow(data)

def process_device(row, register_name_map):
    ip = row['ip'].strip()
    slave_id= int(row['slave'].strip())
    description = row['description'].strip()
    registers_to_read = register_parser(row['start_addr'])

    #Connect to Modbus, No need for slave ID, just keep it constant at 1 per default value
    client = ModbusClient(host=ip, port=502, unit_id=1, auto_open=True, timeout=3.0)

    try:
        #print(f"\nReading from {description} ({ip}, slave {slave_id})")
        client.open()
        #print("Client open:", client.is_open)

        for reg_start in registers_to_read:
            reg_name = register_name_map.get(reg_start, f"Register{reg_start}")
            #print(f"Attempting to read from register {reg_name} (Reg_value={reg_start})")

            #Register themselves are 0 indexed so in order to access 1199 we must sub 1 for example
            regs= client.read_holding_registers(reg_start - 1, 2)

            #Floats/decimals are stored as 16 bytes which means that one float takes up two 8-byte registers.
            #With this being said the data is stored in Little Endian format which means that the rightmost byte
            #represents the most significant bit (MSB) and hence the leftmost byte represents the least significant bit (LSB).
            #Therefore the program reads right to left when converting from bytes to actual digits.
            if regs and len(regs) == 2:
                try:
                    float_value = struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]
                    time_of_data = datetime.now().strftime('%Y-%m-%d %H:%M:%S %p')
                except Exception as e:
                    #print(f"Decode error: {str(e)}")
                    continue

                safe_reg_name = reg_name.replace(" ", "_").replace("/", "-")
                data_row = [time_of_data, description, ip, slave_id, reg_start, reg_name, float_value]
                header = ["Timestamp", "Description", "IP", "Slave", "Register", "Register_Name", "Value"]
                
                output_csv_path= data_dir / f"metered_data_{safe_reg_name}.csv"
                append_to_csv(output_csv_path, data_row, header)
                
            else:
                print(f"Read Failed for {reg_name} ({reg_start})")
                error_path = script_dir / "errors.csv"
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S %p')
                append_to_csv(error_path, [timestamp, ip, reg_start, "Read Failed"], ["Timestamp", "IP", "Register", "Error"])
    except Exception as e:
        print(f"An error occurred while processing device {description} ({ip}): {e}")
    finally:
        client.close()


def pull_data():
    try:
        # Reads specified columns of the excel sheet, specifically the register name
        df = pd.read_excel(excel_path, sheet_name= sheet_name, skiprows= 7, header= 0, usecols = ['Modbus Register Name', 'Modbus\n Register'], engine= 'openpyxl')
        # Removes any missing values
        df = df.dropna(subset = ['Modbus Register Name', 'Modbus\n Register'])
        #Builds the map of all the register names
        register_name_map = {}
        for _, row in df.iterrows():
            reg_value= row['Modbus\n Register']
            register_name_map[reg_value] = row['Modbus Register Name']
    except Exception as e:
        print(f"Read error: {str(e)}")
        pass
    
    try:
        with open(csv_path, 'r') as csv_file:  
            devices= list(csv.DictReader(csv_file))
    except FileNotFoundError:
        print(f"FATAL: Could not find the device list file '{csv_path}'.")
        return
                 
    num_devices = len(devices)
    max_workers = min(num_devices, 32) if num_devices > 0 else 1

    # Change the max_workers to the number of devices you want to read from concurrently
    # This is set to 21 because there are 21 devices in the csv file
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for device_row in devices:
            executor.submit(process_device, device_row, register_name_map)

def archive_old_metered_data_files():
    #Create the main archive directory if it doesn't exist
    source_dir= data_dir
    archive_dir = script_dir / "archived_data"
    
    archive_dir.mkdir(exist_ok=True)
    
    files_to_archive = list(source_dir.glob("metered_data_*.csv"))
    
    if not files_to_archive:
        print("No data files to archive.")
        return
    
    start_time= None
    end_time= None
    
    #Finds the earliest and latest modification times among the files
    for file in files_to_archive:
        mod_time_ts = file.stat().st_mtime
        if start_time is None or mod_time_ts < start_time:
            start_time = mod_time_ts
        if end_time is None or mod_time_ts > end_time:
            end_time = mod_time_ts
            
    #Formats the timestamps for the folder name
    start_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d_%H-%M-%S")
    end_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d_%H-%M-%S")
    
    # Create the new timestamped subfolder
    subfolder_name = f"{start_str}_to_{end_str}"
    subfolder_path = archive_dir / subfolder_name
    subfolder_path.mkdir(exist_ok=True)
    
    print(f"Archiving files to: {subfolder_path}")

    for file in files_to_archive:
        try:
            new_path= subfolder_path / file.name
            file.rename(new_path)
        except Exception as e:
            print(f"Could not archive {file.name}. Error: {e}")
