"""
A script to generate OpenMRS 3 forms from a metadata file in Excel.
"""
import json
import os
import re
import time
import uuid
import openpyxl
import pandas as pd
import zipfile
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Load the configuration settings from config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Extract the configuration settings
METADATA_FILE = os.getenv('METADATA_FILEPATH')
if not METADATA_FILE or METADATA_FILE.strip() == '':
    # If environment variable is not set, just initialize to empty
    METADATA_FILE = ''
    print(f"Warning: METADATA_FILEPATH environment variable not set. Please set it before using the generator functions.")

# Extract other configuration settings from config
TRANSLATION_SECTION_COLUMN = config.get('columns', {}).get('TRANSLATION_SECTION_COLUMN', 'Translation - Section')
TRANSLATION_QUESTION_COLUMN = config.get('columns', {}).get('TRANSLATION_QUESTION_COLUMN', 'Translation - Question')
TRANSLATION_TOOLTIP_COLUMN = config.get('columns', {}).get('TRANSLATION_TOOLTIP_COLUMN', 'Translation - Tooltip')
TRANSLATION_ANSWER_COLUMN = config.get('columns', {}).get('TRANSLATION_ANSWER_COLUMN', 'Translation')

# Since tooltip name is different in metadata, extract it form Configuration
TOOLTIP_COLUMN_NAME = config.get('columns', {}).get('TOOLTIP_COLUMN_NAME')

# Extract column mapping configuration
QUESTION_COLUMN = config.get('columns', {}).get('QUESTION_COLUMN', 'Question')
LABEL_COLUMN = config.get('columns', {}).get('LABEL_COLUMN', 'Label if different')
QUESTION_ID_COLUMN = config.get('columns', {}).get('QUESTION_ID_COLUMN', 'Question ID')
EXTERNAL_ID_COLUMN = config.get('columns', {}).get('EXTERNAL_ID_COLUMN', 'External ID')
DATATYPE_COLUMN = config.get('columns', {}).get('DATATYPE_COLUMN', 'Datatype')
VALIDATION_COLUMN = config.get('columns', {}).get('VALIDATION_COLUMN', 'Validation (format)')
MANDATORY_COLUMN = config.get('columns', {}).get('MANDATORY_COLUMN', 'Mandatory')
RENDERING_COLUMN = config.get('columns', {}).get('RENDERING_COLUMN', 'Rendering')
LOWER_LIMIT_COLUMN = config.get('columns', {}).get('LOWER_LIMIT_COLUMN', 'Lower limit')
UPPER_LIMIT_COLUMN = config.get('columns', {}).get('UPPER_LIMIT_COLUMN', 'Upper limit')
DEFAULT_VALUE_COLUMN = config.get('columns', {}).get('DEFAULT_VALUE_COLUMN', 'Default value')
CALCULATION_COLUMN = config.get('columns', {}).get('CALCULATION_COLUMN', 'Calculation')
SKIP_LOGIC_COLUMN = config.get('columns', {}).get('SKIP_LOGIC_COLUMN', 'Skip logic')
PAGE_COLUMN = config.get('columns', {}).get('PAGE_COLUMN', 'Page')
SECTION_COLUMN = config.get('columns', {}).get('SECTION_COLUMN', 'Section')
OPTION_SET_COLUMN = config.get('columns', {}).get('OPTION_SET_COLUMN', 'OptionSet name')

# Define option_sets as None initially
option_sets = None

# Initialize ALL_QUESTIONS_ANSWERS as an empty list
ALL_QUESTIONS_ANSWERS = []

def read_excel_skip_strikeout(filepath, sheet_name=0, header_row=1):
    """
    Reads an Excel sheet, skipping any row that has strikethrough formatting
    in any cell. Returns a Pandas DataFrame.

    :param filepath: Path to the Excel file
    :param sheet_name: Sheet name or index (0-based) to read
    :param header_row: Which row in Excel is the header (1-based index)
    :return: Pandas DataFrame with rows containing strikethrough removed
    """
    print(f"Reading sheet '{sheet_name}' from file: '{filepath}'")

    if not filepath or filepath.strip() == '':
        raise ValueError("Empty file path provided. Please check your METADATA_FILEPATH environment variable.")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Excel file not found: '{filepath}'")

    try:
        # Load workbook (use data_only=True if you only need computed values)
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb[sheet_name]

        # Convert 1-based to 0-based index for Python lists
        header_idx = header_row - 1

        # Grab all rows as openpyxl cell objects (not values_only=True,
        # so we can read formatting info).
        all_rows = list(ws.iter_rows())

        # Identify the header row cells and extract the column names
        header_cells = all_rows[header_idx]
        column_names = [cell.value for cell in header_cells]

        data = []
        # Iterate over the remaining rows after the header
        for row_idx in range(header_idx + 1, len(all_rows)):
            row_cells = all_rows[row_idx]
            row_has_strike = False
            row_values = []

            for cell in row_cells:
                # Check if the cell has a font and if that font uses strikethrough
                if sheet_name == 'OptionSets':
                    if cell.font and cell.font.strike:
                        row_has_strike = True
                        break  # No need to check other cells in this row
                else:
                    question_cell = row_cells[column_names.index('Question')]
                    if question_cell.font and question_cell.font.strike:
                        row_has_strike = True
                        break  # No need to check other cells in this row
                row_values.append(cell.value)

            if not row_has_strike:
                data.append(row_values)

        # Create a DataFrame from the filtered data
        df = pd.DataFrame(data, columns=column_names)
        return df
    except zipfile.BadZipFile:
        raise zipfile.BadZipFile("The Excel file appears to be corrupted. Please try re-saving it in .xlsx format.")
    except KeyError:
        raise KeyError(f"Sheet '{sheet_name}' not found in the Excel file.")
    except Exception as e:
        # Try using pandas directly as a fallback
        try:
            print(f"Attempting to read {sheet_name} with pandas directly using file: {filepath}")
            # Try with openpyxl engine first
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row-1, engine='openpyxl')
            print(f"Successfully read {sheet_name} with pandas using openpyxl engine.")
            return df
        except Exception as pandas_error_openpyxl:
            try:
                # Try with default engine as fallback (don't specify engine)
                print(f"Attempting with default engine...")
                df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row-1)
                print(f"Successfully read {sheet_name} with pandas using default engine.")
                return df
            except Exception as pandas_error_default:
                raise Exception(f"Error reading Excel file: {str(e)}. "
                               f"Pandas fallback with openpyxl failed: {str(pandas_error_openpyxl)}. "
                               f"Default engine fallback also failed: {str(pandas_error_default)}")

def initialize_option_sets(metadata_file=None):
    """
    Initialize option_sets from the metadata file

    Args:
        metadata_file (str, optional): Path to the metadata file. If None, uses the global METADATA_FILE.
    """
    global option_sets

    # Use the provided metadata_file if available, otherwise use the global METADATA_FILE
    file_to_use = metadata_file if metadata_file else METADATA_FILE

    if not file_to_use or not os.path.exists(file_to_use):
        raise FileNotFoundError(f"Metadata file not found: '{file_to_use}'")

    try:
        option_sets = read_excel_skip_strikeout(filepath=file_to_use, sheet_name='OptionSets', header_row=2)
        
        # Check for duplicate column names and handle them
        if option_sets.columns.duplicated().any():
            print("Warning: Duplicate column names found in OptionSets sheet. Renaming duplicates.")
            # Make column names unique by adding suffixes
            cols = pd.Series(option_sets.columns)
            for dup in cols[cols.duplicated()].unique():
                cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f'{dup}_{i}' for i in range(sum(cols == dup))]
            option_sets.columns = cols
            
    except Exception as e:
        # Try a direct pandas approach as fallback
        try:
            print(f"Attempting to read OptionSets with pandas directly using file: {file_to_use}")
            # Try with openpyxl engine first
            option_sets = pd.read_excel(file_to_use, sheet_name='OptionSets', header=1, engine='openpyxl')
            print("Successfully read OptionSets with pandas using openpyxl engine.")
            
            # Check for duplicate column names and handle them
            if option_sets.columns.duplicated().any():
                print("Warning: Duplicate column names found in OptionSets sheet. Renaming duplicates.")
                cols = pd.Series(option_sets.columns)
                for dup in cols[cols.duplicated()].unique():
                    cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f'{dup}_{i}' for i in range(sum(cols == dup))]
                option_sets.columns = cols
                
        except Exception as pandas_error_openpyxl:
            try:
                # Try with default engine as fallback
                print(f"Attempting with default engine...")
                option_sets = pd.read_excel(file_to_use, sheet_name='OptionSets', header=1)
                print("Successfully read OptionSets with pandas using default engine.")
                
                # Check for duplicate column names and handle them
                if option_sets.columns.duplicated().any():
                    print("Warning: Duplicate column names found in OptionSets sheet. Renaming duplicates.")
                    cols = pd.Series(option_sets.columns)
                    for dup in cols[cols.duplicated()].unique():
                        cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f'{dup}_{i}' for i in range(sum(cols == dup))]
                    option_sets.columns = cols
                    
            except Exception as pandas_error_default:
                raise Exception(f"Failed to read OptionSets sheet: {str(e)}. "
                               f"Pandas fallback with openpyxl failed: {str(pandas_error_openpyxl)}. "
                               f"Default engine fallback also failed: {str(pandas_error_default)}")

# Function to fetch options for a given option set
def get_options(option_set_name, option_sets_override=None):
    """
    Fetch options for a given option set name, sorted by the "Order" column.

    Args:
        option_set_name (str): The name of the option set.
        option_sets_override (pd.DataFrame, optional): Override for option_sets. Defaults to None.

    Returns:
        tuple: A tuple containing (options_list, found_flag) where:
            - options_list is a list of dictionaries containing option set details, sorted by "Order" column
            - found_flag is a boolean indicating if the option set was found
    """
    option_sets_to_use = option_sets_override if option_sets_override is not None else option_sets
    if option_sets_to_use is None:
        raise ValueError("Option sets not initialized. Call initialize_option_sets first.")

    filtered_options = option_sets_to_use[option_sets_to_use['OptionSet name'] == option_set_name]
    options_found = len(filtered_options) > 0

    if options_found:
        # Find the 'Order' column
        order_column = next((col for col in filtered_options.columns if str(col) == 'Order'), None)
        
        if order_column is not None:
            try:
                # Create a copy to avoid modifying the original DataFrame
                filtered_options = filtered_options.copy()
                
                # Convert Order column to numeric, handling non-numeric values as NaN
                filtered_options[order_column] = pd.to_numeric(
                    filtered_options[order_column], 
                    errors='coerce'
                )
                # Sort by the Order column numerically, putting NaN values at the end
                filtered_options = filtered_options.sort_values(
                    by=order_column,
                    na_position='last'
                )
            except Exception as e:
                print(f"Warning: Could not sort by 'Order' column: {str(e)}. Returning unsorted options.")

    # Handle duplicate columns before converting to dict to avoid warnings
    if filtered_options.columns.duplicated().any():
        # Make column names unique by adding suffixes, but keep the original data
        cols = pd.Series(filtered_options.columns)
        for dup in cols[cols.duplicated()].unique():
            cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f'{dup}_{i}' for i in range(sum(cols == dup))]
        filtered_options.columns = cols
    
    return filtered_options.to_dict(orient='records'), options_found

def find_question_concept_by_label(questions_answers, question_label):
    """
    Find question concept by label.

    Args:
        questions_answers (list): List of question answer dictionaries
        question_label (str): The label to search for

    Returns:
        str: The question ID if found, otherwise a generated ID
    """
    if not questions_answers:
        question_id, _, _ = manage_id(question_label)
        return question_id

    for question in questions_answers:
        test_id, _, _ = manage_id(question_label)
        if question.get('question_id') == test_id:
            return question.get('question_id')
    question_id, _, _ = manage_id(question_label)
    return question_id

def find_answer_concept_by_label(questions_answers, question_id, answer_label):
    """
    Find answer concept by label.

    Args:
        questions_answers (list): List of question answer dictionaries
        question_id (str): The question ID to search for
        answer_label (str): The answer label to search for

    Returns:
        str: The answer concept if found, otherwise a generated ID
    """
    if not questions_answers:
        answer_id, _, _ = manage_id(answer_label)
        return answer_id

    for question in questions_answers:
        test_id, _, _ = manage_id(question_id)
        if question.get('question_id') == test_id:
            for answer in question.get('questionOptions', {}).get('answers', []):
                if answer.get('label') == answer_label:
                    return answer.get('concept')
    answer_id, _, _ = manage_id(answer_label)
    return answer_id

def safe_json_loads(s):
    """
    Safe json loads.
    """
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return None

def manage_rendering(rendering):
    """
    Manage rendering options.
    """
    if rendering == 'radio':
        rendering = 'radio'
    elif rendering == 'multicheckbox':
        rendering = 'multiCheckbox'
    elif rendering == 'inlinemulticheckbox':
        rendering = 'multiCheckbox'
    elif rendering == 'boolean':
        rendering = 'radio'
    elif rendering == 'numeric':
        rendering = 'numeric'
    elif rendering == 'text':
        rendering = 'text'
    elif rendering == 'textarea':
        rendering = 'textarea'
    elif rendering == 'decimalnumber':
        rendering = 'number'
    return rendering

def format_label(original_label):
    """
    Format the label.
    """
    # Clean the label
    label = remove_prefixes(original_label)
    # Remove any other non-alphanumeric characters except spaces, (), -, _, /, ., <, > and +
    label = re.sub(r'[^a-zA-Z0-9\s\(\)\-_\/\.<>+]', '', label)
    # Remove leading ". " prefixes
    label = re.sub(r'^\.\s*', '', label)

    return label

def manage_label(original_label):
    """
    Manage labels.

    Args:
        original_label (str): The original label.

    Returns:
        str: The cleaned label.
    """
    # Convert to string to handle integers and other types
    if original_label is None:
        return ""

    # Format the label
    # label = format_label(original_label)

    return str(original_label)

# Dictionary to track ID modifications for skip logic updates
ID_MODIFICATIONS = {}

def reset_id_modifications():
    """
    Reset the ID modifications tracking dictionary.
    Should be called at the start of each form generation.
    """
    global ID_MODIFICATIONS
    ID_MODIFICATIONS.clear()

# Manage IDs
def manage_id(original_id, id_type="question", question_id="None", all_questions_answers=None):
    """
    Manage IDs with enhanced uniqueness checking and tracking.

    Args:
        original_id (str): The original ID.
        id_type (str, optional): The ID type. Defaults to "question".
        question_id (str, optional): The question ID. Defaults to "None".
        all_questions_answers (list, optional): A list of all questions and their answers.
        Defaults to None.

    Returns:
        tuple: A tuple containing (cleaned_id, was_modified, original_label) where:
            - cleaned_id (str): The final unique ID
            - was_modified (bool): Whether the ID was modified to ensure uniqueness
            - original_label (str): The original label before cleaning, for reference
    """
    if all_questions_answers is None:
        all_questions_answers = []

    # Store original label for reference
    original_label = str(original_id) if original_id is not None else ""

    # Handle None or empty values
    if original_id is None:
        return str(uuid.uuid4()), True, original_label

    # Convert to string to handle integers and other types
    original_id = str(original_id)

    cleaned_id = remove_prefixes(original_id)
    cleaned_id = re.sub(r'\s*\(.*?\)', '', cleaned_id)
    # Replace "/" with "Or"
    cleaned_id = re.sub(r'/', ' Or ', cleaned_id)
    if not detect_range_prefixes(cleaned_id):
        # Replace "-" with a space (but not if it was already handled by remove_prefixes)
        if not re.match(r'^\d+[a-zA-Z]', cleaned_id):  # Don't replace if it's already in "1type" format
            cleaned_id = re.sub(r'-', ' ', cleaned_id)
        # Replace "_" with a space
        cleaned_id = re.sub(r'_', ' ', cleaned_id)
    # Replace remaining "-" with "To" for ranges
    if not re.match(r'^\d+[a-zA-Z]', cleaned_id):  # Don't replace if it's already in "1type" format
        cleaned_id = re.sub(r'-', 'To', cleaned_id)
    # Replace "<"
    cleaned_id = re.sub(r'<', 'Less Than', cleaned_id)
    # Replace ">"
    cleaned_id = re.sub(r'>', 'More Than', cleaned_id)
    cleaned_id = camel_case(cleaned_id)
    # Replace '+' characters with 'plus'
    cleaned_id = re.sub(r'\+', 'Plus', cleaned_id)
    # Remove any other non-alphanumeric characters
    cleaned_id = re.sub(r'[^a-zA-Z0-9_-]', '', cleaned_id)
    # Remove leading and trailing underscores
    cleaned_id = re.sub(r'^_+|_+$', '', cleaned_id)
    # Replace multiple underscores with a single underscore
    cleaned_id = re.sub(r'_+', '_', cleaned_id)

    # Handle empty string after cleaning
    if not cleaned_id:
        cleaned_id = f"id_{str(uuid.uuid4()).replace('-', '')[:8]}"
        return cleaned_id, True, original_label

    # Ensure first character is lowercase (only if string is not empty)
    if len(cleaned_id) > 0:
        cleaned_id = cleaned_id[0].lower() + cleaned_id[1:]

    was_modified = False
    if id_type == "answer" and cleaned_id == 'other':
        cleaned_id = str(question_id)+str(cleaned_id.capitalize())
        was_modified = True

    if all_questions_answers is not None:
        duplicate_count = 1
        original_cleaned_id = cleaned_id
        while any(q['question_id'] == cleaned_id for q in all_questions_answers):
            cleaned_id = f"{original_cleaned_id}_{duplicate_count}"
            was_modified = True
            duplicate_count += 1
            # Track the modification for skip logic updates
            if was_modified:
                ID_MODIFICATIONS[original_label] = cleaned_id
                print(f"Warning: Duplicate question ID found. '{original_label}' modified to '{cleaned_id}'")

    return cleaned_id, was_modified, original_label

def remove_prefixes(text):
    """
    Remove numerical prefixes from the beginning of the string.
    Examples of prefixes: "1. ", "1.1 ", "1.1.1 ", etc.
    Special handling for "1 - type" format to become "1type".

    Note: Pure integers (like "1", "2", "3") are preserved as they are likely
    intended as actual answer values, not prefixes.

    Parameters:
    text (str): The input string from which to remove prefixes.

    Returns:
    str: The string with the prefixes removed or transformed.
    """
    if text is None:
        return ""

    # Convert text to string before processing
    text = str(text)

    if not detect_range_prefixes(text):
        # Check if the text is just a pure integer (no spaces or other characters)
        if re.match(r'^\d+$', text):
            # Keep pure integers as they are likely answer values, not prefixes
            return text

        # Special handling for "number - text" format only (e.g., "1 - type" -> "1type")
        # Do NOT modify "text - number" or "text number - text" formats
        dash_pattern = re.match(r'^(\d+)\s*-\s*([^0-9].*)$', text)
        if dash_pattern:
            number_part = dash_pattern.group(1)
            text_part = dash_pattern.group(2)
            return number_part + text_part

        # Use re.sub to remove the matched prefix and any trailing dots/spaces
        text = re.sub(r'^\d+(\.\d+)*[\s\.]*', '', text)
    return text

def detect_range_prefixes(text):
    """
    Detect ranges in the beginning of the string.
    """
    pattern = r"(\d+-\d+|\> \d+|< \d+|\d+ - \d+|\d+-\d+)"
    matches = re.findall(pattern, str(text))  # Convert text to string
    return bool(matches)

def camel_case(text):
    """
    Camel case a string.
    """
    # Convert to string to handle integers and other types
    if text is None:
        return str(uuid.uuid4())

    text = str(text)
    words = text.split()

    # If text is empty, return UUID
    if not words or text == '%':
        return str(uuid.uuid4())

    # Convert the first word to lowercase and capitalize the rest of the words
    camel_case_text = words[0].lower()
    for word in words[1:]:
        camel_case_text += word.capitalize()
    return camel_case_text

def build_skip_logic_expression(expression: str, questions_answers) -> str:
    """
    Build a skip logic expression from an expression string.

    Args:
        expression (str): An expression string. Can include multiple conditions in set notation.
            Example: "Hide question if [BCG] !== {'Unknown', 'Not vaccinated'}"

    Returns:
        str: A skip logic expression.
    """
    # Regex pattern to match comma-separated values
    # Example: [Number of fetuses] !== '1', '2', '3', '4'
    comma_values_pattern = r"\[([^\]]+)\]\s*(<>|!==|==)\s*'[^']+'(?:\s*,\s*'[^']+')*"

    # Regex pattern to match multiple values in set notation
    # Example: [BCG] !== {'Unknown', 'Not vaccinated'}
    multi_value_pattern = r"\[([^\]]+)\]\s*(<>|!==|==)\s*\{(.+?)\}"

    # Regex pattern to match single value condition
    single_value_pattern = r"\[([^\]]+)\]\s*(<>|!==|==)\s*'([^']*)'"

    uuid_pattern = r'[a-fA-F0-9]{8}-' \
                '[a-fA-F0-9]{4}-' \
                '[a-fA-F0-9]{4}-' \
                '[a-fA-F0-9]{4}-' \
                '[a-fA-F0-9]{12}|' \
                '[a-fA-F0-9]{32}'

    # First try to match comma-separated values pattern
    comma_match = re.search(comma_values_pattern, expression)
    if comma_match:
        original_question_label = comma_match.group(1)
        operator = comma_match.group(2)
        
        # Extract all quoted values from the matched expression
        values_part = expression[comma_match.start():comma_match.end()]
        values = re.findall(r"'([^']+)'", values_part)

        # Normalize operator
        if operator == '<>':
            operator = '!=='
        elif operator != '!==' and operator != '==':
            return 'Only conditional operators "different than" (!==/<>) and "equals" (==) are supported'

        # Get question ID
        if re.match(uuid_pattern, original_question_label):
            question_id = original_question_label
        else:
            question_id = find_question_concept_by_label(questions_answers, original_question_label)

        # Build conditions for each value
        conditions = []
        for value in values:
            # Check if value is a UUID
            if re.match(uuid_pattern, value):
                cond_answer = value
            else:
                cond_answer = find_answer_concept_by_label(
                    questions_answers, original_question_label, value
                )
            conditions.append(f"{question_id} {operator} '{cond_answer}'")

        # Join conditions with logical OR if operator is !== (different than)
        # or with logical AND if operator is == (equals)
        logical_operator = ' || ' if operator == '!==' else ' && '
        return '(' + logical_operator.join(conditions) + ')'

    # Then try to match the multi-value pattern
    multi_match = re.search(multi_value_pattern, expression)
    if multi_match:
        original_question_label, operator, values_str = multi_match.groups()

        # Normalize operator
        if operator == '<>':
            operator = '!=='
        elif operator != '!==' and operator != '==':
            return 'Only conditional operators "different than" (!==/&lt;&gt;) and "equals" (==) are supported'

        # Get question ID
        if re.match(uuid_pattern, original_question_label):
            question_id = original_question_label
        else:
            question_id = find_question_concept_by_label(questions_answers, original_question_label)

        # Parse the values from the set notation
        # Split by comma and remove quotes and whitespace
        values = [v.strip().strip('\'"') for v in values_str.split(',')]

        # Build conditions for each value
        conditions = []
        for value in values:
            # Check if value is a UUID
            if re.match(uuid_pattern, value):
                cond_answer = value
            else:
                cond_answer = find_answer_concept_by_label(
                    questions_answers, original_question_label, value
                )
            conditions.append(f"{question_id} {operator} '{cond_answer}'")

        # Join conditions with logical OR if operator is !== (different than)
        # or with logical AND if operator is == (equals)
        logical_operator = ' || ' if operator == '!==' else ' && '
        return '(' + logical_operator.join(conditions) + ')'

    # If not a multi-value pattern, try the single value pattern
    single_match = re.search(single_value_pattern, expression)
    if single_match:
        original_question_label, operator, original_cond_answer = single_match.groups()

        # Normalize operator
        if operator == '<>':
            operator = '!=='
        elif operator != '!==' and operator != '==':
            return 'Only conditional operators "different than" (!==/&lt;&gt;) and "equals" (==) are supported'

        # Get question ID
        if re.match(uuid_pattern, original_question_label):
            question_id = original_question_label
        else:
            question_id = find_question_concept_by_label(questions_answers, original_question_label)

        # Get answer concept
        if re.match(uuid_pattern, original_cond_answer):
            cond_answer = original_cond_answer
        else:
            cond_answer = find_answer_concept_by_label(
                questions_answers, original_question_label, original_cond_answer
            )

        return f"{question_id} {operator} '{cond_answer}'"

    return "Invalid expression format"


def should_render_workspace(question_rendering):
    """
    Check if a workspace should be rendered
    """
    # List of words to check against
    other_render_options = ["radio", "number", "text", "date", "time", "markdown", "select", "checkbox", "toggle", "multiCheckbox", "textarea", "numeric"]

    for word in other_render_options:
        if word in question_rendering:
            return False
    return True

def get_workspace_button_label(button_label):
    """
    Get the button name for the workspace being rendered.
    """
    if button_label == 'immunization-form-workspace':
        button_label = 'Capture patient immunizations'
    elif button_label == 'order-basket':
        button_label = 'Order medications'
    elif button_label == 'appointments-form-workspace':
        button_label = 'Set the next appointment date'
    elif button_label == 'patient-vitals-biometrics-form-workspace':
        button_label = 'Capture patient vitals'
    elif button_label == 'medications-form-workspace':
        button_label = 'Active medications'
    else :
        button_label = 'Open Workspace'
    return button_label

def add_translation(translations, label, translated_string):
    """
    Add a translation to the translations dictionary.
    """
    if translated_string is None:
        # LOG: Translation not present for the provided label
        pass
    if label in translations:
        if translations[label] != translated_string:
            # LOG: Different translations for same label: label
            pass
        else:
            return
    translations[label] = translated_string

def generate_question(row, columns, question_translations, missing_option_sets=None, option_sets_override=None):
    """
    Generate a question JSON from a row of the OptionSets sheet.

    Args:
        row (pandas.Series): A row of the OptionSets sheet.
        columns (list): A list of column names in the OptionSets sheet.
        question_translations (dict): Dictionary to store translations.
        missing_option_sets (list, optional): List to track missing optionSets.

    Returns:
        dict: A question JSON.
    """

    if row.isnull().all() or pd.isnull(row[QUESTION_COLUMN]):
        return None  # Skip empty rows or rows with empty 'Question'

    # Manage values and default values
    # For question label: use "Question" column as default, but use "Label if different" if it's not empty
    original_question_label = (row[LABEL_COLUMN] if LABEL_COLUMN in columns and
                            pd.notnull(row[LABEL_COLUMN]) and str(row[LABEL_COLUMN]).strip() != '' 
                            else row[QUESTION_COLUMN])

    question_label_translation = (
        row[TRANSLATION_QUESTION_COLUMN].replace('"', '').replace("'", '').replace('\\', '/') if TRANSLATION_QUESTION_COLUMN in columns and
                            pd.notnull(row[TRANSLATION_QUESTION_COLUMN]) else None
                            )

    question_label = manage_label(original_question_label)
    
    # For question ID: use "Question ID" column if provided, otherwise generate from "Question" column in camelCase
    original_question_info = (row[TOOLTIP_COLUMN_NAME] if TOOLTIP_COLUMN_NAME in columns and
                            pd.notnull(row[TOOLTIP_COLUMN_NAME]) else None )
    question_info = manage_label(original_question_info)

    if OPTION_SET_COLUMN in columns and pd.notnull(row[OPTION_SET_COLUMN]):
        option_set_name = row[OPTION_SET_COLUMN]
        options, option_set_found = get_options(option_set_name, option_sets_override)
        sorted_options = options
    else:
        option_set_name = None
        options = []
        option_set_found = False
        sorted_options = []

    # For question ID: use "Question ID" column if provided, otherwise generate from "Question" column in camelCase
    if QUESTION_ID_COLUMN in columns and pd.notnull(row[QUESTION_ID_COLUMN]):
        question_id, was_modified, original_label = manage_id(row[QUESTION_ID_COLUMN], all_questions_answers=ALL_QUESTIONS_ANSWERS)
    else:
        # Generate ID from "Question" column (not "Label if different") to ensure consistency
        question_id, was_modified, original_label = manage_id(row[QUESTION_COLUMN], all_questions_answers=ALL_QUESTIONS_ANSWERS)

    # Add the question to ALL_QUESTIONS_ANSWERS early to ensure proper ID tracking
    question_entry = {
        "question_id": question_id,
        "question_label": original_label,
        "questionOptions": {"answers": []}
    }
    ALL_QUESTIONS_ANSWERS.append(question_entry)

    question_concept_id = (row[EXTERNAL_ID_COLUMN] if EXTERNAL_ID_COLUMN in columns and
                        pd.notnull(row[EXTERNAL_ID_COLUMN]) else question_id)

    question_datatype = (row[DATATYPE_COLUMN].lower() if pd.notnull(row[DATATYPE_COLUMN]) else 'radio')

    validation_format = (row[VALIDATION_COLUMN] if VALIDATION_COLUMN in columns and
                        pd.notnull(row[VALIDATION_COLUMN]) else '')

    question_required = (str(row[MANDATORY_COLUMN]).lower() == 'true' if MANDATORY_COLUMN in columns and
                        pd.notnull(row[MANDATORY_COLUMN]) else False)

    question_rendering_value = (row[RENDERING_COLUMN].lower() if pd.notnull(row[RENDERING_COLUMN]) else 'text')

    question_rendering = manage_rendering(question_rendering_value)

    # Build the question JSON
    question = {
        "id": question_id,
        "label": question_label,
        "type": "obs",
        "required": question_required,
    }

    question_options = {
        "rendering": question_rendering,
        "concept": question_concept_id
    }

    # Add min/max values if rendering is numeric/number
    if question_rendering in ['numeric', 'number']:
        if LOWER_LIMIT_COLUMN in columns and pd.notnull(row[LOWER_LIMIT_COLUMN]):
            question_options['min'] = row[LOWER_LIMIT_COLUMN]
        if UPPER_LIMIT_COLUMN in columns and pd.notnull(row[UPPER_LIMIT_COLUMN]):
            question_options['max'] = row[UPPER_LIMIT_COLUMN]

    if should_render_workspace(question_rendering):
        workspace_button_label = get_workspace_button_label(question_rendering)
        question.pop('type')
        question_options = {
            "rendering": "workspace-launcher",
            "buttonLabel": workspace_button_label,
            "workspaceName": question_rendering
        }

    question['questionOptions'] = question_options

    # If question_rendering_value == 'markdown' then append key 'value' with the value similar to the label and change the type key to 'markdown'
    if question_rendering_value == 'markdown':
        question['value'] = [f"## {question_label}"]
        question['type'] = 'markdown'
        question['questionOptions'].pop('concept')

    # If question_rendering_value == 'inlineMultiCheckbox' then append a line in question before 'questionOptions' with '"inlineMultiCheckbox": true,'
    if question_rendering_value == 'inlinemulticheckbox':
        question['inlineMultiCheckbox'] = True

    # Handle decimal numbers based on rendering type
    if question_rendering_value == 'decimalnumber':
        question['disallowDecimals'] = False
    elif question_rendering_value == 'number':
        question['disallowDecimals'] = True

    add_translation(question_translations, question_label, question_label_translation)

    question_validators = safe_json_loads(validation_format)
    if pd.notnull(question_validators):
        question['validators'] = question_validators

    if DEFAULT_VALUE_COLUMN in columns and pd.notnull(row[DEFAULT_VALUE_COLUMN]):
        question['default'] = row[DEFAULT_VALUE_COLUMN]

    if TOOLTIP_COLUMN_NAME in columns and pd.notnull(row[TOOLTIP_COLUMN_NAME]):
        question['questionInfo'] = question_info
        question_info_translation = (
            row[TRANSLATION_TOOLTIP_COLUMN].replace('"', '').replace("'", '').replace('\\', '/')
                if (
                    TRANSLATION_TOOLTIP_COLUMN in columns and
                    pd.notnull(row[TRANSLATION_TOOLTIP_COLUMN])
                ) else None
        )
        add_translation(question_translations, question_info, question_info_translation)

    if CALCULATION_COLUMN in columns and pd.notnull(row[CALCULATION_COLUMN]):
        question['questionOptions']['calculate'] = {"calculateExpression": row[CALCULATION_COLUMN]}

    if SKIP_LOGIC_COLUMN in columns and pd.notnull(row[SKIP_LOGIC_COLUMN]):
        # Update skip logic expression with modified IDs
        skip_logic = row[SKIP_LOGIC_COLUMN]
        for original_label, modified_id in ID_MODIFICATIONS.items():
            # Replace the original label in skip logic with the modified ID
            skip_logic = skip_logic.replace(f"[{original_label}]", f"[{modified_id}]")
        
        question['hide'] = {"hideWhenExpression": build_skip_logic_expression(
            skip_logic, ALL_QUESTIONS_ANSWERS
            )}

    # Add warning if ID was modified
    if was_modified:
        question['idModified'] = True
        question['originalLabel'] = original_label
        question['warning'] = f"Question ID was modified from '{original_label}' to ensure uniqueness"

    question['questionOptions']['answers'] = []

    # Flag if optionSet is not found and option_set_name is not None or empty
    if not option_set_found and option_set_name:
        question['optionSetNotFound'] = True
        question['optionSetName'] = option_set_name
        print(f"Warning: OptionSet '{option_set_name}' not found for question '{question_label}'")

        # Add to missing_option_sets list if provided
        if missing_option_sets is not None:
            missing_option_sets.append({
                "question_id": question_id,
                "question_label": question_label,
                "optionSet_name": option_set_name
            })

        # Add a placeholder answer when optionSet is not found
        # This allows the form to be generated even with missing optionSets
        placeholder_concept, _, _ = manage_id(option_set_name)
        placeholder_answer = {
            "label": f"[Missing OptionSet: {option_set_name}]",
            "concept": f"missing_optionset_{placeholder_concept}"
        }
        question['questionOptions']['answers'].append(placeholder_answer)

        # Add a note in the question to make it clear this is a placeholder
        question['questionOptions']['placeholder'] = True
 
    # Only process options if the optionSet was found
    if option_set_found:
        # Process answers while preserving the order from sorted_options
        answers_list = []
        # sorted_options is already sorted by the Order column from get_options()
        for opt in sorted_options:
            # Handle answer concept generation
            if opt['External ID'] == '#N/A':
                answer_concept, _, _ = manage_id(opt['Answers'])
            elif EXTERNAL_ID_COLUMN in columns and pd.notnull(opt[EXTERNAL_ID_COLUMN]):
                answer_concept = opt['External ID']
            else:
                answer_concept, _, _ = manage_id(opt['Answers'], id_type="answer",
                                               question_id=question_id,
                                               all_questions_answers=ALL_QUESTIONS_ANSWERS)
        
            answer = {
                "label": manage_label(opt['Answers']),
                "concept": answer_concept
            }
            
            # Add to answers_list maintaining the order from sorted_options
            answers_list.append(answer)
            
            # Manage Answer labels
            answer_label = manage_label(opt['Answers'])
            translated_answer_label = (row[TRANSLATION_ANSWER_COLUMN] if TRANSLATION_ANSWER_COLUMN in columns and
                            pd.notnull(row[TRANSLATION_ANSWER_COLUMN]) else None )
            add_translation(question_translations, answer_label, translated_answer_label)

        # Set the answers in the question options, preserving the order
        question['questionOptions']['answers'] = answers_list

    # Update the existing entry in ALL_QUESTIONS_ANSWERS with the final answers
    for qa_entry in ALL_QUESTIONS_ANSWERS:
        if qa_entry['question_id'] == question['id']:
            qa_entry['questionOptions']['answers'] = question['questionOptions']['answers']
            break

    # Pop answers key if answers array is empty
    if 'answers' in question['questionOptions'] and not question['questionOptions']['answers']:
        question['questionOptions'].pop('answers')

    return question

def generate_form(sheet_name, form_translations, metadata_file=None):
    """
    Generate a form JSON from a sheet of the OptionSets sheet.

    Args:
        sheet_name (str): The name of the sheet in the OptionSets sheet.
        form_translations (dict): Dictionary to store translations.
        metadata_file (str, optional): Path to the metadata file. If None, uses the global METADATA_FILE.

    Returns:
        tuple: A tuple containing (form_data, concept_ids_set, count_total_questions, count_total_answers, missing_option_sets)
            where missing_option_sets is a list of dictionaries with information about missing optionSets.
    """
    # Reset the global ALL_QUESTIONS_ANSWERS list and ID modifications tracking
    global ALL_QUESTIONS_ANSWERS
    ALL_QUESTIONS_ANSWERS = []
    reset_id_modifications()

    # Track missing optionSets
    missing_option_sets = []

    form_data = {
        "name": sheet_name,
        "description": "MSF Form - "+sheet_name,
        "version": "1",
        "published": True,
        "uuid": "",
        "processor": "EncounterFormProcessor",
        "encounter": "Consultation",
        "retired": False,
        "referencedForms": [],
        "pages": []
    }

    # Use the provided metadata_file if available, otherwise use the global METADATA_FILE
    file_to_use = metadata_file if metadata_file else METADATA_FILE

    if not file_to_use or not os.path.exists(file_to_use):
        raise FileNotFoundError(f"Metadata file not found: '{file_to_use}'")

    try:
        # Adjust header to start from row 2 and keep Excel font formatting including strike out characters
        df = read_excel_skip_strikeout(filepath=file_to_use, sheet_name=sheet_name, header_row=2)
    except Exception as e:
        # Try a direct pandas approach as fallback
        try:
            print(f"Attempting to read {sheet_name} with pandas directly using file: {file_to_use}")
            # Try with openpyxl engine first
            df = pd.read_excel(file_to_use, sheet_name=sheet_name, header=1, engine='openpyxl')
            print(f"Successfully read {sheet_name} with pandas using openpyxl engine.")
        except Exception as pandas_error_openpyxl:
            try:
                # Try with default engine as fallback
                print(f"Attempting with default engine...")
                df = pd.read_excel(file_to_use, sheet_name=sheet_name, header=1)
                print(f"Successfully read {sheet_name} with pandas using default engine.")
            except Exception as pandas_error_default:
                raise Exception(f"Failed to read sheet {sheet_name}: {str(e)}. "
                               f"Pandas fallback with openpyxl failed: {str(pandas_error_openpyxl)}. "
                               f"Default engine fallback also failed: {str(pandas_error_default)}")

    columns = df.columns.tolist()

    # concept_ids is defined here, not inside the function
    concept_ids_set = set()

    pages = df[PAGE_COLUMN].unique()

    # Keep track of total questions and answers
    count_total_questions = 0
    count_total_answers = 0

    for page in pages:
        page_df = df[df[PAGE_COLUMN] == page]

        form_data["pages"].append({
            "label": f"{page}",
            "sections": []
        })

        for section in page_df[SECTION_COLUMN].unique():
            section_df = page_df[page_df[SECTION_COLUMN] == section]
            section_label = (
                section_df[SECTION_COLUMN].iloc[0] if pd.notnull(section_df[SECTION_COLUMN].iloc[0])
                            else '')

            # Add section label translations to form_translations
            section_label_translation = (
                section_df[TRANSLATION_SECTION_COLUMN].iloc[0].replace('"', '').replace("'", '').replace('\\', '/')
                if TRANSLATION_SECTION_COLUMN in columns and pd.notnull(section_df[TRANSLATION_SECTION_COLUMN].iloc[0])
                else None
            )
            form_translations[section_label] = section_label_translation

            questions = [generate_question(row, columns, form_translations, missing_option_sets)
                        for _, row in section_df.iterrows()
                        if not row.isnull().all() and pd.notnull(row[QUESTION_COLUMN])]

            questions = [q for q in questions if q is not None]

            count_total_questions += len(questions)
            count_total_answers += sum(
                len(q['questionOptions']['answers']) if 'answers' in q['questionOptions']
                else 0 for q in questions
                )

            form_data["pages"][-1]["sections"].append({
                "label": section_label,
                "isExpanded": False,
                "questions": questions
            })

    return form_data, concept_ids_set, count_total_questions, count_total_answers, missing_option_sets

def generate_translation_file(form_name, language, translations_list):
    """
    Generate a translation file JSON.

    Args:
        form_name (str): The name of the form.
        language (str): The language of the translations.
        translations (dict): A dictionary containing the translations.

    Returns:
        dict: A translation file JSON.
    """

    # Reorganize keys in translations_list alphabetically
    ordered_translations_list = {k: v for k, v in sorted(translations_list.items(), key=lambda item: item[0])}

    # Build the translation file JSON
    translation_file = {
        "uuid": "",
        "form": form_name,
        "description": f"{language.capitalize()} Translations for '{form_name}'",
        "language": language,
        "translations": ordered_translations_list
    }

    return translation_file

# Generate forms and save as JSON
OUTPUT_DIR = './generated_form_schemas'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load the data
all_concept_ids = set()
all_forms = []
TOTAL_QUESTIONS = 0
TOTAL_ANSWERS = 0

# Start the timer
start_time = time.time()

# The following code should be removed or commented out:
# for sheet in SHEETS:
#     translations_data = {}
#     form, concept_ids, total_questions, total_answers = generate_form(sheet, translations_data)
#     translations = generate_translation_file(sheet, 'ar', translations_data)
#     json_data = json.dumps(form, indent=2)
#     translations_json_data = json.dumps(translations, ensure_ascii=False, indent=2)
#     try:
#         json.loads(json_data)  # Validate JSON format
#         form_name_output = sheet.replace(" ", "_")
#         with open(os.path.join(OUTPUT_DIR, f"{form_name_output}.json"), 'w', encoding='utf-8') as f:
#             f.write(json_data)
#         print(f"Configuration file for form {sheet} generated successfully!")
#         json.loads(translations_json_data)  # Validate JSON format
#         translation_file_name_output = sheet.replace(" ", "_")
#         with open(os.path.join(OUTPUT_DIR, f"{translation_file_name_output}_translations_ar.json"), 'w', encoding='utf-8') as f:
#             f.write(translations_json_data)
#         print(f"Translation file for form {sheet} generated successfully!")
#         print()
#     except json.JSONDecodeError as e:
#         print(f"JSON format error in form generated from sheet {sheet}: {e}")
#         print(f"JSON format error in translations form generated from sheet {sheet}: {e}")
#     all_concept_ids.update(concept_ids)
#     all_forms.append(form)
#     TOTAL_QUESTIONS += total_questions
#     TOTAL_ANSWERS += total_answers

# # Count the number of forms generated
# FORMS_GENERATED = len(SHEETS)

# # End the timer
# end_time = time.time()

# # Calculate the total time taken
# total_time = end_time - start_time

# # Print the completion message with the number of forms generated
# print("Forms generation completed!")
# print(f"{FORMS_GENERATED} forms generated in {total_time:.2f} seconds")
# print(f"Total number of questions across all forms: {TOTAL_QUESTIONS}")
# print(f"Total number of answers across all forms: {TOTAL_ANSWERS}")
