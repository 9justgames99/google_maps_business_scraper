# -*- coding: utf-8 -*-
# FILE: app.py

"""
Streamlit User Interface for the Google Maps Scraper

This script creates a web interface where a user can input a search query,
set a maximum number of results, choose an output format, and then run the
scraper. It displays live progress and provides a download link for the results.
"""
import streamlit as st
import pandas as pd
from io import BytesIO

# Import the backend scraper logic
import scraper

# --- Helper function for Excel conversion ---
def to_excel(df: pd.DataFrame) -> bytes:
    """Converts a pandas DataFrame to an in-memory Excel file."""
    output = BytesIO()
    # Use the 'xlsxwriter' engine for better compatibility, or 'openpyxl'
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    # The 'with' statement handles writer.close()
    processed_data = output.getvalue()
    return processed_data

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Google Maps Scraper",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Google Maps Business Scraper")
st.caption("A simple tool to scrape business data from Google Maps.")

# --- Session State Initialization ---
# This helps maintain data across reruns (e.g., keeping results after scraping)
if 'scrape_results' not in st.session_state:
    st.session_state.scrape_results = None
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""

# --- User Interface Layout ---
with st.form("scraper_form"):
    query = st.text_input(
        "Enter Search Query", 
        placeholder="e.g., Coffee shops in London",
        help="Enter what you want to search for on Google Maps."
    )
    max_results = st.number_input(
        "Maximum Number of Results to Scrape", 
        min_value=1, 
        value=20, 
        step=10,
        help="Enter the maximum number of business listings you want. The scraper will stop when it reaches this number or when it runs out of results."
    )
    output_format = st.selectbox(
        "Select Output Format", 
        ("CSV", "Excel", "JSON")
    )
    submitted = st.form_submit_button("Start Scraping")

# --- Scraping and Display Logic ---
if submitted:
    if not query:
        st.error("Please enter a search query.")
    else:
        st.session_state.last_query = query # Save the query
        st.session_state.scrape_results = None # Clear previous results
        
        # UI elements for progress display
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        # Define the callback function that updates the UI
        def update_progress(message: str, percentage: float):
            progress_bar.progress(percentage)
            status_text.info(message)

        driver = None
        try:
            with st.spinner("Initializing web driver... This may take a moment."):
                driver = scraper.get_driver()
            
            update_progress("Driver initialized. Starting scrape...", 0.0)
            
            # Run the scraper from the backend file
            results = scraper.scrape_google_maps(driver, query, max_results, update_progress)
            
            if results:
                status_text.success(f"Scraping complete! Found {len(results)} results.")
                st.session_state.scrape_results = pd.DataFrame(results)
            else:
                status_text.warning("Scraping finished, but no data was found.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
        finally:
            if driver:
                driver.quit()
            progress_bar.empty() # Clean up progress bar

# --- Display Results and Download Button ---
if st.session_state.scrape_results is not None:
    st.markdown("---")
    st.subheader("Scraped Data")
    st.dataframe(st.session_state.scrape_results)
    
    df = st.session_state.scrape_results
    query_filename = st.session_state.last_query.replace(" ", "_")[:30]

    # Prepare data for download
    if output_format == "CSV":
        file_data = df.to_csv(index=False).encode('utf-8')
        file_name = f"{query_filename}_results.csv"
        mime_type = "text/csv"
    elif output_format == "Excel":
        file_data = to_excel(df)
        file_name = f"{query_filename}_results.xlsx"
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif output_format == "JSON":
        file_data = df.to_json(orient='records', indent=4).encode('utf-8')
        file_name = f"{query_filename}_results.json"
        mime_type = "application/json"

    st.download_button(
        label=f"📥 Download as {output_format}",
        data=file_data,
        file_name=file_name,
        mime=mime_type
    )