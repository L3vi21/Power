import struct
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from pyModbusTCP.client import ModbusClient

script_dir = Path(__file__).parent
csv_path = script_dir / "ips.csv"
#Path to the DentInstruments register list
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

#Section of code bellow creates a register name map so in order to pull names of registers

df_check = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=10)
print(df_check.columns)

#Reads specified columns of the excel sheet, specifically the register name
df = pd.read_excel(excel_path, sheet_name= sheet_name, skiprows= 6, usecols = ['Modbus Register Name', 'Modbus Register'])
#Removes any missing values
df = df.dropna(subset = ['Modbus Register Name', 'Modbus Register'])
#Builds the map of all the register names
register_name_map = {int(row['Modbus Register']): row['Modbus Register Name'] for _, row in df.iterrows()}

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
            reg_name = register_name_map.get(reg_start, f"Register{reg_start}")
            print(f"Attempting to read from register {reg_name} (Reg_value={reg_start})")

            regs = client.read_holding_registers(reg_start-1, 2)
            
            #Makes sure that the data being stored is a float32 made up of two 16 bit register
            if regs and len(regs) == 2:
                try:
                    float_value = struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]
                
                except Exception as e:
                    print(f"Decode error: {str(e)}")
                    continue

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                safe_reg_name = reg_name.replace(" ", "_").replace("/","-")
                output_file = script_dir / f"metered_data{safe_reg_name}.csv"

                data_row = [timestamp, description, ip, slave_id, reg_start, reg_name, float_value]
                header = ["Timestamp", "Description", "IP", "Slave", "Register", "Register_Name", "Value"]

                append_to_csv(f"metered_data_{safe_reg_name}.csv", data_row, header)
            else:    
                print(f"Read Failed for {reg_name} ({reg_start})")
                error_path = script_dir / "errors.csv"
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                append_to_csv(error_path, [timestamp, ip, reg_start, "Read Failed"], ["Timestamp", "IP", "Register", "Error"])





