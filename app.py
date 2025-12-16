import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import urllib

# --- 1. DATABASE CONNECTION USING SECRETS ---
@st.cache_resource
def get_engine():
    # Fetch values from st.secrets instead of hardcoding
    secret = st.secrets["connections"]["azure_sql"]
    
    params = urllib.parse.quote_plus(
        f"Driver={{{secret['driver']}}};"
        f"Server=tcp:{secret['server']},1433;"
        f"Database={secret['database']};"
        f"Uid={secret['uid']};"
        f"Pwd={secret['pwd']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )
    
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine

# --- 2. DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    engine = get_engine()
    query = "SELECT * FROM zippy_applicants"
    # SQLAlchemy engine avoids the UserWarning
    df = pd.read_sql(query, engine)
    return df

st.set_page_config(page_title="Zippy Sales Portal", layout="wide")
st.title("Tax Credit Eligibility Finder")
st.markdown("Search for candidates eligible for Empowerment Zone tax credits.")

try:
    df = load_data()

    # --- 3. SIDEBAR FILTERS ---
    st.sidebar.header("🔍 Search Filters")
    
    # Text Search for State/City/Zip
    state_filter = st.sidebar.multiselect("State", options=df['state'].unique())
    city_filter = st.sidebar.text_input("City (Type to search)")
    zip_filter = st.sidebar.text_input("Zip Code")
    
    # NAICS Filter
    naics_filter = st.sidebar.multiselect("NAICS Code", options=df['naics_code'].unique())
    
    # Zone Filter (Show only Empowerment Zone hits?)
    ez_only = st.sidebar.checkbox("Show only Empowerment Zone hits", value=False)

    # --- 1. SIDEBAR FILTERS & RELOAD ---
    st.sidebar.header("⚙️ Controls")

    if st.sidebar.button("🔄 Reload Data"):
        st.cache_data.clear()  
        st.rerun()             


    # --- 4. FILTERING LOGIC ---
    filtered_df = df.copy()
    if state_filter:
        filtered_df = filtered_df[filtered_df['state'].isin(state_filter)]
    if city_filter:
        filtered_df = filtered_df[filtered_df['city'].str.contains(city_filter, case=False, na=False)]
    if zip_filter:
        filtered_df = filtered_df[filtered_df['zipcode'].str.contains(zip_filter, na=False)]
    if naics_filter:
        filtered_df = filtered_df[filtered_df['naics_code'].isin(naics_filter)]
    if ez_only:
        filtered_df = filtered_df[filtered_df['zone_result'] != 'N/A']

    # --- 5. SALES METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Candidates Found", len(filtered_df))
    col2.metric("EZ Eligible", len(filtered_df[filtered_df['zone_result'] != 'N/A']))
    col3.metric("Unique NAICS Sectors", filtered_df['naics_code'].nunique())

    # --- 6. GROUPING & ANALYSIS ---
    st.subheader("📊 Grouped Summary")
    group_option = st.selectbox("Group By", ["State", "NAICS Code", "Both"])
    
    if group_option == "State":
        summary = filtered_df.groupby('state').size().reset_index(name='Count')
    elif group_option == "NAICS Code":
        summary = filtered_df.groupby('naics_code').size().reset_index(name='Count')
    else:
        summary = filtered_df.groupby(['state', 'naics_code']).size().reset_index(name='Count')
    
    st.bar_chart(summary.set_index(summary.columns[0])['Count'])

    # --- 7. THE DATA TABLE ---
    st.subheader("📋 Candidate Details")
    # Hide the resume column if you want a cleaner view, or keep it for the link
    st.dataframe(filtered_df, width='stretch')

except Exception as e:
    st.error(f"Could not connect to Azure SQL: {e}")
