# OpenMRS Form Generator

A Python-based tool to generate OpenMRS 3.x form schemas from Excel metadata files.

## Features

### 1. Question ID Generation
- Supports various ID formats:
  - Numbered prefixes: `"1 - type"` → `"1type"`
  - Regular prefixes: `"1. Question"` → `"question"`
  - Maintains uniqueness by appending numbers for duplicates
- IDs are compatible with custom expressions and skip logic

### 2. Skip Logic Support
- Multiple condition formats:
  ```
  # Comma-separated values
  Hide question if [Number of fetuses] !== '1', '2', '3', '4'
  
  # Set notation
  Hide question if [BCG] !== {'Unknown', 'Not vaccinated'}
  
  # Single value
  Hide question if [Question] !== 'Value'
  ```
- Generates proper logical expressions with OR/AND operators
- Maintains compatibility with generated question IDs

### 3. Option Set Handling
- Respects order defined in "#" column of OptionSets tab
- Maintains order in generated JSON schema
- Supports external IDs and translations

### 4. Data Type Support
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

### 5. Translation Support
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
