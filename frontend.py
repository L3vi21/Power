import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import glob
import plotly.express as px
from datetime import datetime
import csv
import string

equip_list= ['PM C4 Substation (OFFLINE)','PM Autoclave 7 (OFFLINE)','PM C1L1 Substation',
              'PM C1L2 Substation','PM C2P Substation','PM Autoclave 5','PM Autoclave 2',
              'PM Autoclave 8','PM C2L Substation','PM C1A Substation','PM B2 Substation',
              'PM B3 Substation','PM A1 Substation','PM Drop Bottom','PM A3 Substation',
              'PM Autoclave 3','PM Autoclave 1','PM Autoclave 10','PM Autoclave 6',
              'PM Autoclave 9','PM Autoclave 4']

channel_lis= ['Channel 1', 'Channel 2', 'Channel 3', 'Avg Channel']

st.set_page_config(page_title= "Power Monitoring", layout= "wide")

with st.sidebar:
    data_range= st.date_input(
        label= "Pick Date Range",
        value= (datetime(2025,6,1), datetime(2025,6,25)),
        min_value= datetime(2025,1,13),
        max_value= datetime(2025,6,25)
    )
    equip_select= st.multiselect(label= "Pick Equipment(s)", options= equip_list)
    channel_select= st.multiselect(label= "Pick Channel(s)", options=channel_lis)
    graph_button= st.button("Graph Data")

    
#path where the csvs are stored
csv_path = Path(__file__).parent
csv_files = list(csv_path.glob("metered_data_*.csv"))

if graph_button and equip_select:
    all_data= []
    
    for equip in equip_select:
        matching_files = list(csv_path.glob(f"metered_data*{equip}*.csv"))

        if not csv_files:
            st.warning("⚠️ No metered data found ⚠️")
            continue

        for file in matching_files:
            with open(file, 'r') as csv_file:
                reader= csv.DictReader(csv_file)
                for row in reader:
                    if file.startswith("PM"):
                        match channel_select:
                            case ''
                        value= row[]
                    value= row[]








            df= pd.read_csv(file, parse_dates=["Timestamp"])
            df= df[df["Timestamp"].between(pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1]))]
            df["Equipment"] = equip

            if not df.empty:
                all_data.append(df)
    
    if all_data:
        combined_df= pd.concat(all_data, ignore_index= True)

        fig = px.line(
            combined_df,
            x="Timestamp",
            y="Value",
            color="Equipment",
            line_group="Register_Name",
            hover_data=["Register_Name", "IP", "Register"]
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data found in the selected date range.")