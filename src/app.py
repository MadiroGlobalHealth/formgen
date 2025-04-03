
import streamlit as st
import pandas as pd
import openpyxl
import os
import json
import uuid
import base64
import zipfile
import sys
import re
import subprocess
from dotenv import load_dotenv

# Function to get the current git commit hash
def get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    except:
        return "unknown"

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

# Load the configuration settings from config.json
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")
        return {"columns": {}}

# Save configuration to config.json
def save_config(config):
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")
        return False

# Function to get default column mappings
def get_default_column_mappings():
    return {
        "TOOLTIP_COLUMN_NAME": "Tooltip",
        "TRANSLATION_SECTION_COLUMN": "Translation - Section",
        "TRANSLATION_QUESTION_COLUMN": "Translation - Question", 
        "TRANSLATION_TOOLTIP_COLUMN": "Translation - Tooltip",
        "TRANSLATION_ANSWER_COLUMN": "Translation",
        "QUESTION_COLUMN": "Question",
        "LABEL_COLUMN": "Label if different",
        "QUESTION_ID_COLUMN": "Question ID",
        "EXTERNAL_ID_COLUMN": "External ID",
        "DATATYPE_COLUMN": "Datatype",
        "VALIDATION_COLUMN": "Validation (format)",
        "MANDATORY_COLUMN": "Mandatory",
        "RENDERING_COLUMN": "Rendering",
        "LOWER_LIMIT_COLUMN": "Lower limit",
        "UPPER_LIMIT_COLUMN": "Upper limit",
        "DEFAULT_VALUE_COLUMN": "Default value",
        "CALCULATION_COLUMN": "Calculation",
        "SKIP_LOGIC_COLUMN": "Skip logic",
        "PAGE_COLUMN": "Page",
        "SECTION_COLUMN": "Section",
        "OPTION_SET_COLUMN": "OptionSet name"
    }

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
        
        # Set the metadata filepath environment variable for the form_generator module
        os.environ['METADATA_FILEPATH'] = metadata_file
        
        # Initialize option sets if not already done
        if not st.session_state.option_sets_initialized:
            initialize_option_sets(metadata_file)
            st.session_state.option_sets_initialized = True
        
        # Load current configuration to ensure it's used
        config = load_config()
        
        # Update form_generator module's configuration variables with current settings
        import src.form_generator as fg
        for key, value in config.get("columns", {}).items():
            if hasattr(fg, key):
                setattr(fg, key, value)
        
        generated_forms = []
        
        for sheet in selected_sheets:
            translations_data = {}
            try:
                # Start timing the generation
                import time
                start_time = time.time()
                
                # Generate form and translations, explicitly passing the metadata file path
                form, _, total_questions, total_answers = generate_form(sheet, translations_data, metadata_file)
                translations = generate_translation_file(sheet, 'ar', translations_data)
                
                # End timing
                generation_time = time.time() - start_time
                
                # Create output directory if it doesn't exist
                output_dir = 'generated_forms'
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate filenames
                form_filename = f"{sheet.replace(' ', '_')}.json"
                translation_filename = f"{sheet.replace(' ', '_')}_translations_ar.json"
                
                form_path = os.path.join(output_dir, form_filename)
                translation_path = os.path.join(output_dir, translation_filename)
                
                # Convert to JSON strings
                form_json = json.dumps(form, indent=2)
                translation_json = json.dumps(translations, indent=2, ensure_ascii=False)
                
                # Calculate file sizes
                form_size = len(form_json.encode('utf-8'))
                translation_size = len(translation_json.encode('utf-8'))
                
                # Count sections and pages
                num_pages = len(form.get('pages', []))
                num_sections = sum(len(page.get('sections', [])) for page in form.get('pages', []))
                
                # Save files
                with open(form_path, 'w', encoding='utf-8') as f:
                    f.write(form_json)
                
                with open(translation_path, 'w', encoding='utf-8') as f:
                    f.write(translation_json)
                
                generated_forms.append({
                    'sheet': sheet,
                    'form_path': form_path,
                    'translation_path': translation_path,
                    'total_questions': total_questions,
                    'total_answers': total_answers,
                    'form_json': form_json,
                    'translation_json': translation_json,
                    'generation_time': generation_time,
                    'form_size': form_size,
                    'translation_size': translation_size,
                    'num_pages': num_pages,
                    'num_sections': num_sections
                })
                
                st.success(f"Successfully generated form for {sheet}")
            
            except Exception as e:
                st.error(f"Error generating form for sheet {sheet}: {str(e)}")
                st.info(f"Skipping sheet {sheet} and continuing with the next one.")
        
        return generated_forms
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return []

def show_configuration_page():
    st.title("🔧 Column Mapping Configuration")
    st.markdown("""
    ### Customize Excel Column Mappings
    
    Modify the column names used by the form generator to match your Excel file structure.
    """)
    
    # Load current configuration
    config = load_config()
    column_mappings = config.get("columns", get_default_column_mappings())
    
    # Check if we have saved settings in localStorage
    if 'column_mappings' in st.session_state:
        column_mappings = st.session_state.column_mappings
    
    # Create a form for the configuration
    with st.form("column_mapping_form"):
        # Group related fields
        st.subheader("Basic Question Fields")
        col1, col2 = st.columns(2)
        with col1:
            column_mappings["QUESTION_COLUMN"] = st.text_input("Question Column", column_mappings.get("QUESTION_COLUMN", "Question"))
            column_mappings["LABEL_COLUMN"] = st.text_input("Label Column", column_mappings.get("LABEL_COLUMN", "Label if different"))
            column_mappings["QUESTION_ID_COLUMN"] = st.text_input("Question ID Column", column_mappings.get("QUESTION_ID_COLUMN", "Question ID"))
            column_mappings["EXTERNAL_ID_COLUMN"] = st.text_input("External ID Column", column_mappings.get("EXTERNAL_ID_COLUMN", "External ID"))
        
        with col2:
            column_mappings["DATATYPE_COLUMN"] = st.text_input("Datatype Column", column_mappings.get("DATATYPE_COLUMN", "Datatype"))
            column_mappings["RENDERING_COLUMN"] = st.text_input("Rendering Column", column_mappings.get("RENDERING_COLUMN", "Rendering"))
            column_mappings["MANDATORY_COLUMN"] = st.text_input("Mandatory Column", column_mappings.get("MANDATORY_COLUMN", "Mandatory"))
            column_mappings["TOOLTIP_COLUMN_NAME"] = st.text_input("Tooltip Column", column_mappings.get("TOOLTIP_COLUMN_NAME", "Tooltip"))
        
        st.subheader("Form Structure Fields")
        col1, col2 = st.columns(2)
        with col1:
            column_mappings["PAGE_COLUMN"] = st.text_input("Page Column", column_mappings.get("PAGE_COLUMN", "Page"))
            column_mappings["SECTION_COLUMN"] = st.text_input("Section Column", column_mappings.get("SECTION_COLUMN", "Section"))
            column_mappings["OPTION_SET_COLUMN"] = st.text_input("Option Set Column", column_mappings.get("OPTION_SET_COLUMN", "OptionSet name"))
        
        st.subheader("Validation and Logic Fields")
        col1, col2 = st.columns(2)
        with col1:
            column_mappings["VALIDATION_COLUMN"] = st.text_input("Validation Column", column_mappings.get("VALIDATION_COLUMN", "Validation (format)"))
            column_mappings["LOWER_LIMIT_COLUMN"] = st.text_input("Lower Limit Column", column_mappings.get("LOWER_LIMIT_COLUMN", "Lower limit"))
            column_mappings["UPPER_LIMIT_COLUMN"] = st.text_input("Upper Limit Column", column_mappings.get("UPPER_LIMIT_COLUMN", "Upper limit"))
        
        with col2:
            column_mappings["DEFAULT_VALUE_COLUMN"] = st.text_input("Default Value Column", column_mappings.get("DEFAULT_VALUE_COLUMN", "Default value"))
            column_mappings["CALCULATION_COLUMN"] = st.text_input("Calculation Column", column_mappings.get("CALCULATION_COLUMN", "Calculation"))
            column_mappings["SKIP_LOGIC_COLUMN"] = st.text_input("Skip Logic Column", column_mappings.get("SKIP_LOGIC_COLUMN", "Skip logic"))
        
        st.subheader("Translation Fields")
        col1, col2 = st.columns(2)
        with col1:
            column_mappings["TRANSLATION_SECTION_COLUMN"] = st.text_input("Translation Section Column", column_mappings.get("TRANSLATION_SECTION_COLUMN", "Translation - Section"))
            column_mappings["TRANSLATION_QUESTION_COLUMN"] = st.text_input("Translation Question Column", column_mappings.get("TRANSLATION_QUESTION_COLUMN", "Translation - Question"))
        
        with col2:
            column_mappings["TRANSLATION_TOOLTIP_COLUMN"] = st.text_input("Translation Tooltip Column", column_mappings.get("TRANSLATION_TOOLTIP_COLUMN", "Translation - Tooltip"))
            column_mappings["TRANSLATION_ANSWER_COLUMN"] = st.text_input("Translation Answer Column", column_mappings.get("TRANSLATION_ANSWER_COLUMN", "Translation"))
        
        # Add buttons for saving and resetting
        col1, col2, col3 = st.columns(3)
        with col1:
            save_button = st.form_submit_button("Save Configuration")
        
        with col2:
            reset_button = st.form_submit_button("Reset to Defaults")
        
        with col3:
            download_button = st.form_submit_button("Download Config")
    
    # Handle form submission
    if save_button:
        # Save to session state
        st.session_state.column_mappings = column_mappings
        
        # Save to config.json
        config["columns"] = column_mappings
        if save_config(config):
            st.success("Configuration saved successfully!")
        
        # Store in localStorage using Streamlit's component
        st.markdown(
            """
            <script>
            localStorage.setItem('formGeneratorConfig', JSON.stringify(
                """ + json.dumps(column_mappings) + """
            ));
            </script>
            """,
            unsafe_allow_html=True
        )
    
    if reset_button:
        # Reset to defaults
        default_mappings = get_default_column_mappings()
        st.session_state.column_mappings = default_mappings
        config["columns"] = default_mappings
        if save_config(config):
            st.success("Configuration reset to defaults!")
        st.rerun()  # Updated from st.experimental_rerun()
    
    if download_button:
        # Create a downloadable config file
        config_json = json.dumps({"columns": column_mappings}, indent=4)
        b64 = base64.b64encode(config_json.encode()).decode()
        href = f'<a href="data:file/json;base64,{b64}" download="config.json">Download config.json</a>'
        st.markdown(href, unsafe_allow_html=True)

def main():
    # Set page config first - this must be the first Streamlit command
    st.set_page_config(
        page_title="OpenMRS Form Generator",
        page_icon="🏥",
        layout="wide"
    )
    
    # Initialize session state for JSON preview toggles and generated forms
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.generated_forms = []
        st.session_state.temp_file_path = None
        st.session_state.selected_sheets = []
        st.session_state.forms_generated = False
        st.session_state.option_sets_initialized = False
        st.session_state.current_page = "home"
        
        # Try to load saved config from localStorage
        st.markdown(
            """
            <script>
            const savedConfig = localStorage.getItem('formGeneratorConfig');
            if (savedConfig) {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: JSON.parse(savedConfig),
                    key: 'loaded_config'
                }, '*');
            }
            </script>
            """,
            unsafe_allow_html=True
        )

    # Create a sidebar container with custom CSS for vertical alignment
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: flex;
            flex-direction: column;
        }
        .sidebar-content {
            flex-grow: 1;
        }
        .sidebar-footer {
            margin-top: auto;
            text-align: center;
            padding-bottom: 20px;
        }
        </style>
        <div class="sidebar-content">
        """, 
        unsafe_allow_html=True
    )
    
    # Navigation menu
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "",
        ["O3 Form Generator", "Configuration"],
        key="navigation"
    )
    
    # Close the content div and start the footer
    st.sidebar.markdown("</div><div class='sidebar-footer'>", unsafe_allow_html=True)
    
    # Add "Powered by" text and Madiro logo at the bottom of the sidebar
    st.sidebar.markdown("<p style='color: #888; font-size: 0.8em;'>Powered by</p>", unsafe_allow_html=True)
    st.sidebar.image(
        "https://raw.githubusercontent.com/MadiroGlobalHealth/clinical-content-tools/refs/heads/main/.github/workflows/madiro.png",
        width=100
    )
    
    # Add version number (git commit hash) below the logo
    commit_hash = get_git_commit()
    st.sidebar.markdown(f"<p style='color: #888; font-size: 0.7em;'>Version: {commit_hash}</p>", unsafe_allow_html=True)
    
    # Close the footer div
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    
    if page == "O3 Form Generator":
        st.session_state.current_page = "home"
        show_home_page()
    elif page == "Configuration":
        st.session_state.current_page = "config"
        show_configuration_page()

def show_home_page():
    st.title("🏥 OpenMRS 3 Form Generator")
    st.markdown("""
    ### Generate OpenMRS 3 Form Schemas from Excel Metadata
    
    Verify the mappings with the column names in your Excel file in the Configuration page, then upload an Excel file containing form metadata to generate JSON schemas.
    """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an Excel file", 
        type=['xlsx', 'xlsm', 'xltx', 'xltm'],
        help="Upload an Excel file with form metadata. Supported formats: .xlsx, .xlsm, .xltx, .xltm"
    )

    if uploaded_file is not None:
        
        # Save the uploaded file
        with st.spinner('Processing file... Please wait.'):
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
        
        # Initialize option sets from the uploaded file only if not already initialized
        if not st.session_state.option_sets_initialized:
            with st.spinner('Initializing option sets... Please wait.'):
                try:
                    initialize_option_sets(temp_file_path)
                    st.session_state.option_sets_initialized = True
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
        
        # Extract sheet names and filter for sheets starting with "F" followed by 2 digits
        wb = openpyxl.load_workbook(temp_file_path, read_only=True)
        all_sheet_names = wb.sheetnames
        
        # Filter sheets that start with "F" followed by 2 digits
        form_sheet_names = [sheet for sheet in all_sheet_names if re.match(r'^F\d{2}', sheet)]
        
        # Sheet selection with checkboxes
        st.subheader("Select Sheets to Generate Forms")
        
        # Create columns for checkboxes to make better use of space
        num_cols = 3  # Number of columns for checkboxes
        cols = st.columns(num_cols)
        
        selected_sheets = []
        for i, sheet in enumerate(form_sheet_names):
            col_idx = i % num_cols
            with cols[col_idx]:
                if st.checkbox(sheet, key=f"sheet_{sheet}"):
                    selected_sheets.append(sheet)
        
        # Show selected count
        if selected_sheets:
            st.info(f"Selected {len(selected_sheets)} sheets: {', '.join(selected_sheets)}")

        # Generate forms button
        generate_button = st.button("Generate Forms", type="primary")
        
        if generate_button or st.session_state.forms_generated:
            if not selected_sheets and not st.session_state.forms_generated:
                st.warning("Please select at least one sheet")
            else:
                # Only generate forms if they haven't been generated yet or if the button was just clicked
                if generate_button and not st.session_state.forms_generated:
                    # Create a full-page spinner overlay
                    with st.spinner('Generating forms... Please wait, this may take a few minutes.'):
                        st.session_state.temp_file_path = temp_file_path
                        st.session_state.selected_sheets = selected_sheets
                        st.session_state.generated_forms = generate_forms_from_sheets(temp_file_path, selected_sheets)
                        st.session_state.forms_generated = True
                
                # Display results using the stored generated forms
                st.subheader("Generated Forms")
                
                for form in st.session_state.generated_forms:
                    st.markdown(f"### Form: {form['sheet']}")
                    
                    # Create a 2x2 grid for metrics
                    metric_cols = st.columns(4)
                    with metric_cols[0]:
                        st.metric("Questions", form['total_questions'])
                    with metric_cols[1]:
                        st.metric("Answers", form['total_answers'])
                    with metric_cols[2]:
                        st.metric("Pages", form.get('num_pages', 'N/A'))
                    with metric_cols[3]:
                        st.metric("Sections", form.get('num_sections', 'N/A'))
                    
                    # Add generation stats
                    stat_cols = st.columns(3)
                    with stat_cols[0]:
                        st.metric("Generation Time", f"{form.get('generation_time', 0):.2f}s")
                    with stat_cols[1]:
                        form_size_kb = form.get('form_size', 0) / 1024
                        st.metric("Form Size", f"{form_size_kb:.1f} KB")
                    with stat_cols[2]:
                        trans_size_kb = form.get('translation_size', 0) / 1024
                        st.metric("Translation Size", f"{trans_size_kb:.1f} KB")
                    
                    # Create columns for form and translation
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Form JSON
                        form_json = form['form_json']
                        
                        # Download button
                        st.download_button(
                            label="Download Form JSON",
                            data=form_json,
                            file_name=os.path.basename(form['form_path']),
                            mime='application/json'
                        )
                        
                        # Add collapsible JSON preview
                        with st.expander("Preview Form JSON (click to expand)"):
                            st.code(form_json, language="json")
                    
                    with col2:
                        # Translation JSON
                        translation_json = form['translation_json']
                        
                        # Download button
                        st.download_button(
                            label="Download Translation JSON",
                            data=translation_json,
                            file_name=os.path.basename(form['translation_path']),
                            mime='application/json'
                        )
                        
                        # Add collapsible JSON preview
                        with st.expander("Preview Translation JSON (click to expand)"):
                            st.code(translation_json, language="json")
                    
                    st.markdown("---")  # Add a separator between forms

if __name__ == "__main__":
    main()
