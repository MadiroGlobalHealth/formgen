"""
Test suite for the OpenMRS Form Generator
"""
import unittest
import sys
import os
import pandas as pd
import json
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from form_generator import (
    manage_id,
    remove_prefixes,
    build_skip_logic_expression,
    get_options,
    generate_question,
    manage_rendering
)

class TestFormGenerator(unittest.TestCase):
    """Test cases for form generator functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_questions_answers = [
            {
                "question_id": "numberOfFetuses",
                "question_label": "Number of fetuses",
                "questionOptions": {
                    "answers": [
                        {"label": "1", "concept": "9c407911-f329-4761-b27a-bbbe24cc0332"},
                        {"label": "2", "concept": "42965304-8abb-4a57-b7c2-b3eff5cbe9c7"},
                        {"label": "3", "concept": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
                        {"label": "4", "concept": "b2c3d4e5-f6g7-8901-bcde-f23456789012"}
                    ]
                }
            }
        ]

    def test_remove_prefixes_dash_format(self):
        """Test removal of dash prefixes like '1 - type'"""
        test_cases = [
            ("1 - type", "1type"),
            ("2 - category", "2category"),
            ("10 - description", "10description"),
            ("1-type", "1type"),  # No spaces
            ("3  -  test", "3test"),  # Multiple spaces
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = remove_prefixes(input_text)
                self.assertEqual(result, expected)

    def test_remove_prefixes_regular_format(self):
        """Test removal of regular numerical prefixes"""
        test_cases = [
            ("1. Question", "Question"),  # Should remove number and dot
            ("1.1 Subquestion", "Subquestion"),  # Should remove all prefixes
            ("2.3.4 Deep question", "Deep question"),  # Should remove all prefixes
            ("1", "1"),  # Pure integer should be preserved
            ("2", "2"),  # Pure integer should be preserved
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = remove_prefixes(input_text)
                self.assertEqual(result, expected)

    def test_manage_id_dash_format(self):
        """Test ID generation with dash format"""
        test_cases = [
            ("1 - type", "1type"),
            ("2 - category", "2category"),
            ("10 - long description", "10longDescription"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = manage_id(input_text)
                self.assertEqual(result, expected)

    def test_manage_id_uniqueness(self):
        """Test that duplicate IDs are made unique"""
        existing_questions = [
            {"question_id": "testQuestion"},
            {"question_id": "testQuestion_1"}
        ]
        
        result = manage_id("Test Question", all_questions_answers=existing_questions)
        self.assertEqual(result, "testQuestion_2")

    def test_build_skip_logic_comma_separated(self):
        """Test skip logic with comma-separated values"""
        expression = "Hide question if [Number of fetuses] !== '1', '2', '3', '4'"
        result = build_skip_logic_expression(expression, self.sample_questions_answers)
        
        expected_parts = [
            "numberOfFetuses !== '9c407911-f329-4761-b27a-bbbe24cc0332'",
            "numberOfFetuses !== '42965304-8abb-4a57-b7c2-b3eff5cbe9c7'",
            "numberOfFetuses !== 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'",
            "numberOfFetuses !== 'b2c3d4e5-f6g7-8901-bcde-f23456789012'"
        ]
        
        for part in expected_parts:
            self.assertIn(part, result)
        self.assertTrue(result.startswith('(') and result.endswith(')'))

    def test_build_skip_logic_set_notation(self):
        """Test skip logic with set notation"""
        expression = "Hide question if [Number of fetuses] !== {'1', '2'}"
        result = build_skip_logic_expression(expression, self.sample_questions_answers)
        
        expected_parts = [
            "numberOfFetuses !== '9c407911-f329-4761-b27a-bbbe24cc0332'",
            "numberOfFetuses !== '42965304-8abb-4a57-b7c2-b3eff5cbe9c7'"
        ]
        
        for part in expected_parts:
            self.assertIn(part, result)
        self.assertTrue(" || " in result)

    def test_build_skip_logic_single_value(self):
        """Test skip logic with single value"""
        expression = "Hide question if [Number of fetuses] !== '1'"
        result = build_skip_logic_expression(expression, self.sample_questions_answers)
        
        # Single value expressions are wrapped in parentheses by comma pattern
        expected = "(numberOfFetuses !== '9c407911-f329-4761-b27a-bbbe24cc0332')"
        self.assertEqual(result, expected)

    def test_manage_rendering(self):
        """Test rendering type management"""
        test_cases = [
            ("radio", "radio"),
            ("multicheckbox", "multiCheckbox"),
            ("inlinemulticheckbox", "multiCheckbox"),
            ("boolean", "radio"),
            ("numeric", "numeric"),
            ("text", "text"),
            ("textarea", "textarea"),
            ("decimalnumber", "number"),
        ]
        
        for input_rendering, expected in test_cases:
            with self.subTest(input=input_rendering):
                result = manage_rendering(input_rendering)
                self.assertEqual(result, expected)

    @patch('form_generator.option_sets')
    def test_get_options_sorting(self, mock_option_sets):
        """Test that options are sorted by '#' column"""
        # Create mock DataFrame with '#' column
        mock_data = pd.DataFrame({
            'OptionSet name': ['TestSet', 'TestSet', 'TestSet'],
            'Answers': ['Option C', 'Option A', 'Option B'],
            '#': [3, 1, 2],
            'External ID': ['uuid3', 'uuid1', 'uuid2']
        })
        
        mock_option_sets.value = mock_data
        mock_option_sets.__getitem__ = lambda self, key: mock_data[key]
        mock_option_sets.columns = mock_data.columns
        
        # Mock the filtering
        filtered_mock = mock_data[mock_data['OptionSet name'] == 'TestSet']
        mock_option_sets.__getitem__.return_value = filtered_mock
        
        with patch('form_generator.option_sets', mock_data):
            options, found = get_options('TestSet')
            
            # Verify options are sorted by '#' column
            self.assertTrue(found)
            self.assertEqual(len(options), 3)
            # After sorting by '#', order should be: Option A (1), Option B (2), Option C (3)
            expected_order = ['Option A', 'Option B', 'Option C']
            actual_order = [opt['Answers'] for opt in options]
            self.assertEqual(actual_order, expected_order)

    def test_generate_question_decimal_handling(self):
        """Test decimal number handling in question generation"""
        # Mock row data for decimalnumber
        decimal_row = pd.Series({
            'Question': 'Test Decimal',
            'Rendering': 'decimalnumber',
            'Datatype': 'numeric'
        })
        
        # Mock row data for number
        number_row = pd.Series({
            'Question': 'Test Number',
            'Rendering': 'number',
            'Datatype': 'numeric'
        })
        
        columns = ['Question', 'Rendering', 'Datatype']
        translations = {}
        
        # Test decimalnumber
        with patch('form_generator.manage_id', return_value='testDecimal'):
            decimal_question = generate_question(decimal_row, columns, translations)
            self.assertFalse(decimal_question['disallowDecimals'])
        
        # Test number
        with patch('form_generator.manage_id', return_value='testNumber'):
            number_question = generate_question(number_row, columns, translations)
            self.assertTrue(number_question['disallowDecimals'])


class TestIntegration(unittest.TestCase):
    """Integration tests for the form generator"""
    
    def test_id_generation_with_skip_logic(self):
        """Test that generated IDs work correctly with skip logic"""
        # Test that a question with "1 - type" format generates correct ID
        question_id = manage_id("1 - type")
        self.assertEqual(question_id, "1type")
        
        # Test that this ID works in skip logic
        questions_answers = [{
            "question_id": "1type",
            "question_label": "1 - type",
            "questionOptions": {
                "answers": [
                    {"label": "Yes", "concept": "yes-uuid"},
                    {"label": "No", "concept": "no-uuid"}
                ]
            }
        }]
        
        expression = "Hide question if [1 - type] !== 'Yes', 'No'"
        result = build_skip_logic_expression(expression, questions_answers)
        
        # Should contain the generated ID
        self.assertIn("1type", result)
        self.assertIn("yes-uuid", result)
        self.assertIn("no-uuid", result)


if __name__ == '__main__':
    # Create test directory if it doesn't exist
    os.makedirs('tests', exist_ok=True)
    
    # Run the tests
    unittest.main(verbosity=2)
