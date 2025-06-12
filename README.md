 # OpenMRS Form Generator

A Python-based tool to generate OpenMRS 3.x form schemas from Excel metadata files.

## Features

### 1. Enhanced Question ID Generation
- Supports various ID formats:
  - Simple number-dash-text: `"1 - type"` → `"1type"` (concatenated)
  - Text-dash-number: `"Type - 1"` → `"Type - 1"` (preserved)
  - Complex patterns: `"Type 1 - Gynaecology"` → `"Type 1 - Gynaecology"` (preserved)
  - Regular prefixes: `"1. Question"` → `"question"`
- **Maintains uniqueness by appending numbers for duplicates**:
  - When a duplicate ID is detected, the script appends an incrementing number to the ID (e.g., `question_1`, `question_2`).
  - The original question label is preserved and a warning is added to the question.
- IDs are compatible with custom expressions and skip logic

### 2. Answer Options Handling
- **Numeric sorting** by "#" column in OptionSets:
  - Proper numeric order: 1, 2, 3, 10, 20 (not alphabetical)
  - Supports decimal numbers (e.g., 1.5)
  - Consistent sorting across form generation

### 3. Skip Logic Support
- Multiple condition formats:
  ```
  # Comma-separated values
  Hide question if [Number of fetuses] !== '1', '2', '3', '4'
  ```
  
  ```
  # Set notation
  Hide question if [BCG] !== {'Unknown', 'Not vaccinated'}
  ```
  
  ```
  # Single value
  Hide question if [Question] !== 'Value'
  ```
- Generates proper logical expressions with OR/AND operators
- **Maintains compatibility with generated question IDs**:
  - Skip logic expressions are automatically updated to use modified question IDs, ensuring that skip logic remains functional even when IDs are changed.

### 4. Option Set Handling
- **Numeric sorting** by "#" column of OptionSets tab (1, 2, 3, 10, 20 - not 1, 10, 2, 20, 3)
- Supports decimal numbers in "#" column (e.g., 1.5 between 1 and 2)
- Non-numeric values in "#" column are placed at the end
- Maintains sorted order in generated JSON schema
- Handles duplicate column names gracefully (uses first occurrence)
- Supports external IDs and translations

### 5. Data Type Support
- Decimal number handling:
  - `decimalnumber` rendering: allows decimals (`"disallowDecimals": false`)
  - `number` rendering: disallows decimals (`"disallowDecimals": true`)
- Various rendering types:
  - radio
  - multiCheckbox
  - inlineMultiCheckbox
  - boolean
  - numeric
  - text
  - textarea
  - markdown
  - workspace-launcher

### 6. Translation Support
- Generates translation files for form labels
- Supports section, question, tooltip, and answer translations
- Maintains alphabetical order in translation files

## Excel Metadata Format

### Required Sheets
1. Form sheets (e.g., F01, F02, etc.)
   - Contains form structure and questions
   - Columns:
     - Question
     - Label if different
     - Question ID
     - External ID
     - Datatype
     - Rendering
     - OptionSet name
     - Page
     - Section
     - Skip logic
     - Translation columns

2. OptionSets sheet
   - Contains answer options for questions
   - Columns:
     - "#" (for ordering)
     - OptionSet name
     - Answers
     - External ID

## Generated Output

### Form Schema
```json
{
  "name": "Form Name",
  "pages": [{
    "label": "Page Name",
    "sections": [{
      "label": "Section Name",
      "questions": [{
        "id": "questionId",
        "label": "Question Label",
        "questionOptions": {
          "rendering": "radio",
          "answers": [{
            "label": "Answer Label",
            "concept": "answer-uuid"
          }]
        }
      }]
    }]
  }]
}
```

### Translation File
```json
{
  "form": "Form Name",
  "language": "ar",
  "translations": {
    "Answer Label": "Translated Answer",
    "Question Label": "Translated Question",
    "Section Name": "Translated Section"
  }
}
```

## Usage

1. Prepare Excel metadata file following the required format
2. Configure column mappings in config.json if needed
3. Run the form generator:
   ```python
   from form_generator import generate_form, generate_translation_file
   
   # Initialize option sets
   initialize_option_sets('metadata.xlsx')
   
   # Generate form
   form_data, _, _, _, _ = generate_form('F01', translations_data)
   
   # Generate translations
   translations = generate_translation_file('F01', 'ar', translations_data)
   ```

## Testing

Run the test suite:
```bash
python -m unittest tests/test_form_generator.py -v
```

The test suite covers:
- Question ID generation
- Skip logic expressions
- Option set ordering
- Decimal number handling
- Translation generation

## Configuration

Use `config.json` to customize:
- Column mappings
- Sheet filter prefix
- Default values
- Translation settings

Example config:
```json
{
  "columns": {
    "QUESTION_COLUMN": "Question",
    "LABEL_COLUMN": "Label if different",
    "OPTION_SET_COLUMN": "OptionSet name"
  },
  "settings": {
    "SHEET_FILTER_PREFIX": "F\\d{2}"
  }
}
