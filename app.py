from flask import Flask, jsonify, render_template, request
import pandas as pd
import glob
import os
from datetime import datetime, timedelta
import traceback

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
    print("Refreshing data from CSVs...")
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

@app.route('/api/data')
def get_chart_data():
    try:
        equipment = request.args.get('equipment')
        register = request.args.get('register')
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate') 

        if not equipment or not register:
            return jsonify({"error": "Equipment and Register parameters are required."}), 400

        if main_df.empty:
            return jsonify([])
            
        filtered_df = main_df.copy()
        
        # Apply the specific filters
        mask = (filtered_df['Description'] == equipment) & (filtered_df['Register_Name'] == register)
        filtered_df = filtered_df[mask]
        
        # Handle date filtering
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            filtered_df = filtered_df[filtered_df['Timestamp'] >= start_date] 

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            filtered_df = filtered_df[filtered_df['Timestamp'] < end_date]
        
        # **FIX:** Replace NaN with None for valid JSON conversion
        # This prevents the "Unexpected token 'N'" error on the frontend.
        cleaned_df = filtered_df.where(pd.notna(filtered_df), None)

        print(f"DEBUG: Returning {len(cleaned_df)} rows for {equipment} | {register}.")
        return jsonify(cleaned_df.to_dict(orient='records'))

    except Exception as e:
        # Log the full error to the server console for debugging
        print(f"An error occurred in /api/data: {e}")
        traceback.print_exc()
        # Return a JSON error response to the client
        return jsonify({"error": "An internal server error occurred.", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
