from flask import Flask, jsonify, render_template, request
import pandas as pd
import glob
import os
from datetime import datetime, timedelta

app= Flask(__name__)

def get_data_from_csvs():
    data_directory= "metered_data"

    if not os.path.exists(data_directory):
        print(f"WARNING: Data directory for {data_directory} not found")
        return pd.DataFrame()
    
    file_pattern = os.path.join(data_directory, '**', '*.csv')
    all_files = glob.glob(file_pattern, recursive=True)
    
    #Debugging print
    #print(f"Here are the files:{all_files}")
    
    if not all_files:
        print(f"Warning: No .csv files found in '{data_directory}'.")
        return pd.DataFrame()
    
    df_list= []
    for file in all_files:
        try:
            df= pd.read_csv(file, header= 0)

            if 'Timestamp' not in df.columns:
                print(f"Skipping file (missing 'Timestamp'): {file}")
                print(f"Available columns: {df.columns.tolist()}")
                continue
            
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y/%m/%d %I:%M:%S %p', errors='coerce')
            df= df_list.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if not df_list:
        print("No valid dataframes to concatenate.")
        return pd.DataFrame()

    df = pd.concat(df_list, ignore_index=True)
    df = df.sort_values(by='Timestamp')

    print("Data Loading Complete")
    return df

main_df= get_data_from_csvs()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/filters')
def get_filters():
    if main_df.empty:
        return jsonify({
            'equipments': [],
            'registers': []
        })
        
    equipments = main_df['Description'].unique().tolist()
    registers = main_df['Register_Name'].unique().tolist()
    return jsonify({
        'equipments': sorted(equipments),
        'registers': sorted(registers)
    })

@app.route('/api/data')
def get_chart_data():
    if main_df.empty:
        return jsonify([])
        
    filtered_df = main_df.copy()

    equipment = request.args.get('equipment')
    register = request.args.get('register')
    start_date_str = request.args.get('startDate')
    end_date_str = request.args.get('endDate')

    #Apply filters
    if equipment and equipment != 'All Equipment':
        filtered_df = filtered_df[filtered_df['Description'] == equipment]

    if register and register != 'All Registers':
        filtered_df = filtered_df[filtered_df['Register_Name'] == register]

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        filtered_df = filtered_df[filtered_df['Timestamp'] >= start_date]

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        filtered_df = filtered_df[filtered_df['Timestamp'] < end_date]
    
    return jsonify(filtered_df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)