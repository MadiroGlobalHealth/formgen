# OpenMRS 3 Form Generator

A small app that generates OpenMRS 3 form schemas from Excel metadata files.

Use online: [formgen.streamlit.app](https://formgen.streamlit.app)

## Overview

The OpenMRS 3 Form Generator simplifies the process of creating form schemas for OpenMRS 3 by allowing users to define form structure and content in Excel spreadsheets. The application converts these spreadsheets into the required JSON schema format for OpenMRS 3 forms.

## Features

- **Excel-based Form Definition**: Define forms using familiar Excel spreadsheets
- **Configurable Column Mappings**: Customize column names to match your Excel structure
- **Sheet Filtering**: Filter which Excel sheets to process using configurable regex patterns
- **Form Preview**: Preview generated JSON schemas before downloading
- **Translation Support**: Generate translation files for multilingual forms
- **Batch Processing**: Generate multiple forms at once

## Getting Started

### Running the Application

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   streamlit run src/app.py
   ```

### Using the Application

1. **Configure Column Mappings**: Navigate to the Configuration page to set up column mappings that match your Excel file structure
2. **Upload Excel File**: Upload your Excel file containing form metadata
3. **Select Sheets**: Choose which sheets to process
4. **Generate Forms**: Click "Generate Forms" to create JSON schemas
5. **Download Results**: Download the generated form schemas and translation files

## Excel File Format

The Excel file should contain:

- One sheet per form, with sheet names matching the configured filter pattern (default: F01, F02, etc.)
- An "OptionSets" sheet defining answer options
- Columns for form structure (pages, sections, questions)
- Columns for question properties (datatype, rendering, validation, etc.)
- Optional translation columns

## Configuration

The application allows customization of:

- Column name mappings to match your Excel structure
- Sheet filter patterns to identify form sheets
- Other application settings

## Development

### Project Structure

- `src/app.py`: Main Streamlit application
- `src/form_generator.py`: Core form generation logic
- `config.json`: Application configuration


## Acknowledgements

Powered by [Madiro Global Health](https://madiro.org)

<img src="https://raw.githubusercontent.com/MadiroGlobalHealth/clinical-content-tools/refs/heads/main/.github/workflows/madiro.png" alt="Madiro Logo" width="150" />
