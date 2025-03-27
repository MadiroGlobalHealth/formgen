import streamlit as st
import pandas as pd
import openpyxl
import os
import json
import uuid
import base64
import zipfile
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set the metadata filepath environment variable to None initially
# This will prevent the form_generator module from trying to load a non-existent file on import
os.environ['METADATA_FILEPATH'] = ''

# Import the existing form generation functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.form_generator import (
    generate_form, 
    generate_translation_file,
    initialize_option_sets
)

def get_download_link(filepath, filename):
    """
    Generate a download link for a file
    """
    with open(filepath, 'rb') as f:
        bytes = f.read()
        b64 = base64.b64encode(bytes).decode()
        href = f'<a href="data:file/json;base64,{b64}" download="{filename}">Download {filename}</a>'
        return href

def generate_forms_from_sheets(metadata_file, selected_sheets):
    """
    Generate forms from selected sheets
    """
    try:
        # Validate the Excel file first
        try:
            openpyxl.load_workbook(metadata_file, read_only=True)
        except Exception as e:
            st.error(f"Invalid Excel file format: {str(e)}")
            st.info("Please ensure your file is in .xlsx, .xlsm, .xltx, or .xltm format and not corrupted.")
            st.info("If the file was created or saved with a newer version of Excel, try saving it as 'Excel Workbook (.xlsx)' using compatibility mode.")
            return []
        
        # Set the environment variable for the metadata file path
        os.environ['METADATA_FILEPATH'] = metadata_file
        
        # Initialize option sets with the uploaded file
        try:
            initialize_option_sets(metadata_file)
        except Exception as e:
            st.error(f"Error initializing option sets: {str(e)}")
            st.info("Please ensure your Excel file has a sheet named 'OptionSets' with the expected format.")
            st.info("If you're still having issues, try opening the file in Excel and saving it as a new .xlsx file.")
            return []
        
        generated_forms = []
        
        for sheet in selected_sheets:
            translations_data = {}
            try:
                # Generate form and translations, explicitly passing the metadata file path
                form, _, total_questions, total_answers = generate_form(sheet, translations_data, metadata_file)
                translations = generate_translation_file(sheet, 'ar', translations_data)
                
                # Create output directory if it doesn't exist
                output_dir = 'generated_forms'
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate filenames
                form_filename = f"{sheet.replace(' ', '_')}.json"
                translation_filename = f"{sheet.replace(' ', '_')}_translations_ar.json"
                
                form_path = os.path.join(output_dir, form_filename)
                translation_path = os.path.join(output_dir, translation_filename)
                
                # Save files
                with open(form_path, 'w', encoding='utf-8') as f:
                    json.dump(form, f, indent=2)
                
                with open(translation_path, 'w', encoding='utf-8') as f:
                    json.dump(translations, f, indent=2, ensure_ascii=False)
                
                generated_forms.append({
                    'sheet': sheet,
                    'form_path': form_path,
                    'translation_path': translation_path,
                    'total_questions': total_questions,
                    'total_answers': total_answers
                })
                
                st.success(f"Successfully generated form for {sheet}")
            
            except Exception as e:
                st.error(f"Error generating form for sheet {sheet}: {str(e)}")
                st.info(f"Skipping sheet {sheet} and continuing with the next one.")
        
        return generated_forms
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return []

def main():
    st.set_page_config(
        page_title="OpenMRS Form Generator",
        page_icon="🏥",
        layout="wide"
    )

    st.title("🏥 OpenMRS 3 Form Generator")
    st.markdown("""
    ### Generate OpenMRS 3 Form Schemas from Excel Metadata
    
    Upload an Excel file containing form metadata and generate JSON schemas for OpenMRS 3.
    """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an Excel file", 
        type=['xlsx', 'xlsm', 'xltx', 'xltm'],
        help="Upload an Excel file with form metadata. Supported formats: .xlsx, .xlsm, .xltx, .xltm"
    )

    if uploaded_file is not None:
        # Display file info
        st.info(f"File uploaded: {uploaded_file.name} ({uploaded_file.type})")
        
        # Save the uploaded file
        with st.spinner('Processing file...'):
            # Create uploads directory if it doesn't exist
            os.makedirs('uploads', exist_ok=True)
            
            temp_file_path = os.path.join('uploads', uploaded_file.name)
            
            # Save the file
            with open(temp_file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"File saved successfully at {temp_file_path}")
            
            # Validate the file format
            try:
                wb = openpyxl.load_workbook(temp_file_path, read_only=True, data_only=True)
                sheet_names = wb.sheetnames
                wb.close()
            except zipfile.BadZipFile:
                st.error("The uploaded file appears to be corrupted or not a valid Excel file.")
                st.info("Please try re-saving your Excel file or creating a new one. Make sure to save it in .xlsx format.")
                st.stop()
            except Exception as e:
                st.error(f"Error opening Excel file: {str(e)}")
                st.info("Please ensure your file is in a supported Excel format (.xlsx, .xlsm, .xltx, .xltm) and not corrupted.")
                st.stop()
        
        # Initialize option sets from the uploaded file
        try:
            initialize_option_sets(temp_file_path)
        except zipfile.BadZipFile:
            st.error("The uploaded file appears to be corrupted or not a valid Excel file.")
            st.info("Please try re-saving your Excel file or creating a new one. Make sure to save it in .xlsx format.")
            st.stop()
        except Exception as e:
            st.error(f"Error initializing option sets: {str(e)}")
            st.info("Please ensure your Excel file has a sheet named 'OptionSets' with the expected format.")
            st.stop()
        
        # Update environment variable for metadata file path
        os.environ['METADATA_FILEPATH'] = temp_file_path
        
        # Extract sheet names
        wb = openpyxl.load_workbook(temp_file_path, read_only=True)
        sheet_names = wb.sheetnames
        
        # Sheet selection
        st.subheader("Select Sheets to Generate Forms")
        selected_sheets = st.multiselect(
            "Choose sheets", 
            sheet_names,
            help="Select one or more sheets to generate forms"
        )

        # Generate forms button
        if st.button("Generate Forms", type="primary"):
            if not selected_sheets:
                st.warning("Please select at least one sheet")
            else:
                with st.spinner('Generating forms...'):
                    generated_forms = generate_forms_from_sheets(temp_file_path, selected_sheets)
                
                # Display results
                st.subheader("Generated Forms")
                
                for form in generated_forms:
                    with st.expander(f"Form: {form['sheet']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Total Questions", form['total_questions'])
                            
                            # Load form JSON
                            with open(form['form_path'], 'r') as f:
                                form_json = f.read()
                            
                            # Download and copy buttons side by side
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                st.download_button(
                                    label="Download Form JSON",
                                    data=form_json,
                                    file_name=os.path.basename(form['form_path']),
                                    mime='application/json'
                                )
                            with btn_col2:
                                # Copy button using st.code with copy button
                                st.text("Copy Form JSON")
                                st.code(form_json, language="json")
                            
                            # Show collapsed JSON
                            with st.expander("View Form JSON"):
                                st.json(json.loads(form_json))
                        
                        with col2:
                            st.metric("Total Answers", form['total_answers'])
                            
                            # Load translation JSON
                            with open(form['translation_path'], 'r') as f:
                                translation_json = f.read()
                            
                            # Download and copy buttons side by side
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                st.download_button(
                                    label="Download Translation JSON",
                                    data=translation_json,
                                    file_name=os.path.basename(form['translation_path']),
                                    mime='application/json'
                                )
                            with btn_col2:
                                # Copy button using st.code with copy button
                                st.text("Copy Translation JSON")
                                st.code(translation_json, language="json")
                            
                            # Show collapsed JSON
                            with st.expander("View Translation JSON"):
                                st.json(json.loads(translation_json))

if __name__ == "__main__":
    main()
