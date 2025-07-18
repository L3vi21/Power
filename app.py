from flask import Flask, jsonify, render_template, request
import pandas as pd
import glob
import os
from datetime import datetime, timedelta

app= Flask(__name__)

def get_data_from_csvs():
    archive_directory= "archived_data"
    live_data_directory= "metered_data"

    if not os.path.exists(archive_directory):
        print(f"WARNING: Data directory for {archive_directory} not found")
    if not os.path.exists(live_data_directory):
        print(f"WARNING: Data directory for {live_data_directory} not found")
    
    archive_pattern= os.path.join(archive_directory,'**','*.csv')
    live_pattern = os.path.join(live_data_directory,'*.csv')
    all_files = glob.glob(archive_pattern, recursive=True) + glob.glob(live_pattern)
    
    #Debugging print
    #print(f"Here are the files:{all_files}")
    
    if not all_files:
        print("Warning: No .csv files found.")
        return pd.DataFrame()
    
    df_list= []
    for file in all_files:
        try:
            if os.path.getsize(file) == 0:
                print(f"Skipping empty file: {file}")
                continue
            
            df= pd.read_csv(file, header= 0)

            if 'Timestamp' not in df.columns:
                print(f"Skipping file (missing 'Timestamp'): {file}")
                print(f"Available columns: {df.columns.tolist()}")
                continue
            
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S %p', errors='coerce')
            df.dropna(subset=['Timestamp'], inplace=True)
            df_list.append(df)
            
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if not df_list:
        print("No valid dataframes to concatenate.")
        return pd.DataFrame()

    combined_df = pd.concat(df_list, ignore_index=True)
    combined_df = combined_df.sort_values(by='Timestamp')

    print("Data Loading Complete")
    return combined_df

# This function will be called by the scheduler
def refresh_data():
    global main_df
    print("Refreshing data from archived CSVs...")
    main_df = get_data_from_csvs()
    print(f"Data refresh complete. {len(main_df)} rows loaded.")

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
        
    equipments = sorted([str(e) for e in main_df['Description'].unique() if pd.notna(e)])
    registers = sorted([str(r) for r in main_df['Register_Name'].unique() if pd.notna(r)])
    return jsonify({
        'equipments': sorted(equipments),
        'registers': sorted(registers)
    })

# In app.py

@app.route('/api/data')
def get_chart_data():
    equipment = request.args.get('equipment')
    register = request.args.get('register')
    start_date_str = request.args.get('startDate')
    end_date_str = request.args.get('endDate') 

    # NEW: Check if specific filters have been applied.
    # If not, return an empty list to prevent sending too much data.
    if not equipment or equipment == 'All Equipment' or not register or register == 'All Registers':
        print("DEBUG: No specific equipment/register selected. Returning empty list to prevent browser overload.")
        return jsonify([])

    # If specific filters ARE provided, proceed as normal.
    if main_df.empty:
        return jsonify([])
        
    filtered_df = main_df.copy()
    
    # Apply the specific filters that are now required
    filtered_df = filtered_df[(filtered_df['Description'] == equipment) & (filtered_df['Register_Name'] == register)]
    
    start_date= None
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        filtered_df = filtered_df[filtered_df['Timestamp'] >= start_date] 

    end_date = None
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        filtered_df = filtered_df[filtered_df['Timestamp'] < end_date]

    if not filtered_df.empty:
        # Set the Timestamp as the index for resampling
        df_to_resample = filtered_df.set_index('Timestamp')
        
        # Determine the time range to decide on a resampling rule
        time_delta = (df_to_resample.index.max() - df_to_resample.index.min()) if start_date and end_date else timedelta(days=0)
        
        # Define a resampling rule based on the time delta
        if time_delta > timedelta(days=30):
            rule = 'D'  # Daily average
        elif time_delta > timedelta(days=7):
            rule = 'H'  # Hourly average
        elif time_delta > timedelta(days=1):
            rule = 'T'  # Minutely average
        else:
            rule = None # No resampling for short periods
            
        if rule:
            print(f"DEBUG: Resampling data with rule: {rule}")
            # Resample the 'Value' column, then reset the index to get 'Timestamp' back as a column
            resampled_df = df_to_resample['Value'].resample(rule).mean().reset_index()
            # Since resampling might remove other columns, we'll just send what's necessary for the chart
            # Or, you could merge back other relevant info if needed. For now, this is simpler.
            resampled_df['Description'] = equipment
            resampled_df['Register_Name'] = register
            filtered_df = resampled_df

    print(f"DEBUG: Returning {len(filtered_df)} rows for specific selection.")
    return jsonify(filtered_df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)