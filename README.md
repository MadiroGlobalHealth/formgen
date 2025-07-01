# OpenMRS Form Generator (`formgen`)

A Python-based tool to generate OpenMRS 3.x form schemas from Excel metadata files. Designed for rapid, robust, and flexible form creation, supporting advanced skip logic, translations, and a wide range of question types.

---

## 🚀 Features

### 1. **Flexible Question ID Generation**
- Supports various ID formats:
  - `"1 - type"` → `"1type"`
  - `"Type - 1"` → `"Type - 1"`
  - `"Type 1 - Gynaecology"` → `"Type 1 - Gynaecology"`
  - `"1. Question"` → `"question"`
- Ensures uniqueness by appending numbers for duplicates (e.g., `question_1`, `question_2`).
- IDs are compatible with skip logic and custom expressions.

### 2. **Advanced Answer Option Handling**
- Numeric sorting by `#` column in OptionSets (e.g., 1, 2, 3, 10, 20).
- Supports decimal numbers (e.g., 1.5).
- Handles duplicate column names gracefully.
- Supports external IDs and answer translations.

### 3. **Comprehensive Skip Logic Support**
- Supports single value, comma-separated, and set notation conditions:
  - `[Question] !== 'Value'`
  - `[Question] !== '1', '2', '3'`
  - `[Question] !== {'A', 'B'}`
- **Multi-select skip logic:**  
  For questions with `multiCheckbox` or `inlineMultiCheckbox` rendering, skip logic uses `includes`/`!includes`:
  - Example: `!includes(preoperativeDiagnosis, 'uuid')`
- Logical operators:
  - Uses `&&` for multiple conditions.
  - Automatically updates skip logic to use modified question IDs.
- Maintains compatibility with generated question IDs, even if IDs are changed for uniqueness.

### 4. **Option Set Handling**
- Numeric and decimal sorting by `#` column.
- Non-numeric values are placed at the end.
- Maintains sorted order in generated JSON.
- Handles duplicate columns and missing option sets with clear warnings.

### 5. **Data Type & Rendering Support**
- Supports a wide range of rendering types:
  - `radio`, `multiCheckbox`, `inlineMultiCheckbox`, `boolean`, `numeric`, `number`, `text`, `textarea`, `markdown`, `workspace-launcher`
- Decimal number handling:
  - `decimalnumber` rendering: allows decimals (`"disallowDecimals": false`)
  - `number` rendering: disallows decimals (`"disallowDecimals": true`), sets `min`, `max` (from metadata), and `step: 1`
- Custom min/max/step for numeric fields, using metadata columns.

### 6. **Translation Support**
- Generates translation files for form labels, sections, tooltips, and answers.
- Maintains alphabetical order in translation files.

---

## 📊 Excel Metadata Format

### Required Sheets

#### 1. **Form Sheets** (e.g., F01, F02, etc.)
- Columns:
  - `Question`
  - `Label if different`
  - `Question ID`
  - `External ID`
  - `Datatype`
  - `Rendering`
  - `OptionSet name`
  - `Page`
  - `Section`
  - `Skip logic`
  - Translation columns (for questions, tooltips, answers)

#### 2. **OptionSets Sheet**
- Columns:
  - `#` (for ordering)
  - `OptionSet name`
  - `Answers`
  - `External ID`

---

## 📝 Generated Output

### Form Schema Example
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
          "rendering": "multiCheckbox",
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

### Translation File Example
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

---

## ⚡ Usage

1. Prepare your Excel metadata file following the required format.
2. Configure column mappings in `config.json` if needed.
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

---

## 🧪 Testing

Run the test suite:
```bash
python -m unittest tests/test_form_generator.py -v
```
Test coverage includes:
- Question ID generation and uniqueness
- Skip logic (including multi-select logic)
- Option set ordering and handling
- Decimal and numeric field handling
- Translation generation

---

## ⚙️ Configuration

Customize via `config.json`:
- Column mappings
- Sheet filter prefix (regex)
- Default values
- Translation settings

Example:
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
```

---

## ✅ Supported Features Summary

- [x] Unique, robust question ID generation
- [x] Numeric and decimal option set sorting
- [x] Multi-select skip logic with `includes`/`!includes`
- [x] Single, comma, and set notation skip logic
- [x] All major OpenMRS 3.x rendering types
- [x] Custom min/max/step for numeric fields
- [x] Full translation support (questions, answers, tooltips, sections)
- [x] Handles duplicate columns and missing option sets
- [x] Comprehensive test suite

---

If you have questions or need help with advanced features, please open an issue or contact the maintainers.
