import struct
import csv
import sys
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

#Creates the "Canvas" for the UI ()
current_canvas= None

#Number of samples taken per meter
num_samples= 5
#Delay in seconds between each data read
sample_delay= 300
#Function defintions:

#Creates the functionality for the "Clear Graph" button
def clear_graphs():
    for widget in graph_frame.winfo_children():
        if isinstance(widget, FigureCanvasTkAgg):
            widget.get_tk_widget().destroy()            
        else:
            widget.destroy()

#Graphs the desired values against the datetime axis
def show_graph():
    global current_canvas
    selected_option = combobox.get()
    selected_meter= meter_combobox.get()
    
    if not selected_option or not meter_combobox:
        return

    if not overlay_mode.get():
        clear_graphs()
        current_canvas = None

    csv_name= selected_option
    file_path= script_dir / csv_name

    if file_path.exists():
        df = pd.read_csv(file_path)
        df = df[df['Description'] == selected_meter].tail(num_samples)
        
        if df.empty:
            print(f"No data for meter '{selected_meter}' in file '{csv_name}'")
            return
        
        print(df)
        timestamps = pd.to_datetime(df['Time'])
        values= df['Value']

        if overlay_mode.get() and current_canvas:
            fig= current_canvas.figure
            ax= fig.axes[0]
            ax.plot(timestamps, values, label= selected_option)
            ax.legend()
            current_canvas.draw()
        else:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(timestamps, values, label=selected_option)
            ax.set_title(f"{selected_option} - {selected_meter}")
            ax.set_xlabel("Timestamp")
            ax.set_ylabel("Value")
            ax.legend()
            ax.grid(True)
            fig.tight_layout()

            new_canvas= FigureCanvasTkAgg(fig, master= graph_frame)
            new_canvas.draw()
            new_canvas.get_tk_widget().pack(side='top', fill='x', expand= False, pady= 10)
            current_canvas= new_canvas

def quit_program():
    sys.exit(0)

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

#Tkinter main application window for frontend
root = ttk.Window(themename="darkly")
root.geometry("1920x1080")
#Controls whether multiple sets of data go on the same graph
overlay_mode = ttk.BooleanVar(value=False)

#Frame for the graphs tp live in instead of the entire window
graph_frame= ttk.Frame(root, padding= "10 10 10 10")
graph_frame.pack(fill='both', expand=True)

#Button to display the graph
show_button= ttk.Button(root, text= "Graph", bootstyle= (SUCCESS, OUTLINE))
show_button.pack(side= LEFT, padx= 5, pady= 10)
show_button.config(command=show_graph)

#Clear all button, in order to clear window
clear_button= ttk.Button(root, text="Clear Graphs", bootstyle=(DANGER, OUTLINE), command=clear_graphs)
clear_button.pack(side=LEFT, padx= 5, pady= 10)

#Quit Button in order to shut down the program
quit_button= ttk.Button(root, text= "Quit", bootstyle=(LIGHT,OUTLINE), command= quit_program)
quit_button.pack(side= LEFT, padx= 5, pady= 10)

#Button controlling controlling whether multiple data sets will be printed to the same graph
overlay_check = ttk.Checkbutton(root, text="Append to Graph", variable=overlay_mode, bootstyle="info")
overlay_check.pack(side=LEFT, padx=5, pady=10)

#Drop down item to list all the possible data sets to graph
options= ['metered_data_Apparent_PF_CH1_(MSW).csv', 'metered_data_Apparent_PF_CH2_(MSW).csv', 
           'metered_data_Apparent_PF_CH3_(MSW).csv', 'metered_data_Apparent_PF_Avg_Element_(MSW).csv']
combobox= ttk.Combobox(root, bootstyle= "success", values= options)
combobox.set('Data Set Selection')
combobox.pack(side = 'top', fill= 'x', padx= 5, pady= 10)

#Drop down item to list all the possible meters to pull data from
meter_names= ['PM C4 Substation (OFFLINE)','PM Autoclave 7 (OFFLINE)','PM C1L1 Substation',
              'PM C1L2 Substation','PM C2P Substation','PM Autoclave 5','PM Autoclave 2',
              'PM Autoclave 8','PM C2L Substation','PM C1A Substation','PM B2 Substation',
              'PM B3 Substation','PM A1 Substation','PM Drop Bottom','PM A3 Substation',
              'PM Autoclave 3','PM Autoclave 1','PM Autoclave 10','PM Autoclave 6',
              'PM Autoclave 9','PM Autoclave 4']
meter_combobox= ttk.Combobox(root, bootstyle= SUCCESS, values= meter_names, textvariable= 'Meter Selection')
meter_combobox.set('Meter Selection')
meter_combobox.pack(side= 'top', fill= 'x', padx= 5, pady= 10)

#Finds the parent file path
script_dir = Path(__file__).parent
csv_path = script_dir / "ips.csv"
#Path to the DentInstruments register list
excel_path = script_dir / 'PSHD_MASTER_REGISTER_LIST_current-4.xlsx'
sheet_name = "A"

#df_check = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=10, skiprows= 7)
#print(df_check.columns)

#Section of code bellow creates a register name map so in order to pull names of registers
#-----------------------------------------------------------------------------------------

#Reads specified columns of the excel sheet, specifically the register name
df = pd.read_excel(excel_path, sheet_name= sheet_name, skiprows= 7, header= 0, usecols = ['Modbus Register Name', 'Modbus\n Register'], engine= 'openpyxl')
#print(df.columns.tolist())

#Removes any missing values
df = df.dropna(subset = ['Modbus Register Name', 'Modbus\n Register'])

#Builds the map of all the register names
register_name_map = {}
for _, row in df.iterrows():
    reg_value= row['Modbus\n Register']
    register_name_map[reg_value] = row['Modbus Register Name']

#register_name_map = {int(row['Modbus\n Register']): row['Modbus Register Name'] for _, row in df.iterrows()}

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

        for _ in range(num_samples):
            for reg_start in registers:
                reg_name = register_name_map.get(reg_start, f"Register{reg_start}")
                print(f"Attempting to read from register {reg_name} (Reg_value={reg_start})")

                regs = client.read_holding_registers(reg_start-1, 2)
            
                #Makes sure that the data being stored is a float32 made up of two 16 bit register
                if regs and len(regs) == 2:
                    try:
                        # First the data is packed using the little endian format and the data type is an unsigned int
                        # represented by '>HH'. Then the data is unpacked, making sure to get the msb first then the lsb,
                        # it is then stored in a tuple, more specifically the first index.
                        # 
                        float_value = struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]
                        time_of_data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                    except Exception as e:
                        print(f"Decode error: {str(e)}")
                        continue
                    

                    safe_reg_name = reg_name.replace(" ", "_").replace("/","-")
                    output_file = script_dir / f"metered_data{safe_reg_name}.csv"

                    data_row = [time_of_data, description, ip, slave_id, reg_start, reg_name, float_value]
                    header = ["Time", "Description", "IP", "Slave", "Register", "Register_Name", "Value"]

                    append_to_csv(f"metered_data_{safe_reg_name}.csv", data_row, header)
                else:    
                    print(f"Read Failed for {reg_name} ({reg_start})")
                    error_path = script_dir / "errors.csv"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    append_to_csv(error_path, [timestamp, ip, reg_start, "Read Failed"], ["Timestamp", "IP", "Register", "Error"])
            #Adds a delay between consecutive reads
            time.sleep(sample_delay)

root.mainloop()
