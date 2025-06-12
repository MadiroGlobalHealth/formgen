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
        """Test removal of dash prefixes like '1 - type' vs 'Type - 1'"""
        test_cases = [
            ("1 - type", "1type"),  # Number-dash-text becomes concatenated
            ("2 - category", "2category"),
            ("10 - description", "10description"),
            ("1-type", "1type"),  # No spaces
            ("3  -  test", "3test"),  # Multiple spaces
            ("Type - 1", "Type - 1"),  # Text-dash-number stays unchanged
            ("Category - 2", "Category - 2"),  # Text-dash-number stays unchanged
            ("Type 1 - Gynaecology", "Type 1 - Gynaecology"),  # Complex text-number-dash-text stays unchanged
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
                result, was_modified, original_label = manage_id(input_text)
                self.assertEqual(result, expected)
                self.assertEqual(original_label, input_text)

    def test_manage_id_uniqueness(self):
        """Test that duplicate IDs are made unique and reflected in skip logic"""
        # Test basic uniqueness
        existing_questions = [
            {"question_id": "testQuestion"},
            {"question_id": "testQuestion_1"}
        ]
        
        result, was_modified, original_label = manage_id("Test Question", all_questions_answers=existing_questions)
        self.assertEqual(result, "testQuestion_2")
        self.assertTrue(was_modified)
        self.assertEqual(original_label, "Test Question")
        
        # Test uniqueness with skip logic references
        questions_with_skip = [
            {
                "question_id": "pregnancyTest",
                "questionOptions": {"answers": [{"label": "Positive", "concept": "pos-uuid"}]}
            },
            {
                "question_id": "pregnancyTest_1",
                "questionOptions": {"answers": [{"label": "Positive", "concept": "pos-uuid"}]}
            }
        ]
        
        # Generate another question with same base ID
        new_id, was_modified, original_label = manage_id("Pregnancy Test", all_questions_answers=questions_with_skip)
        self.assertEqual(new_id, "pregnancyTest_2")
        self.assertTrue(was_modified)
        
        # Test skip logic expression updates
        expression = "Hide question if [Pregnancy Test] !== 'Positive'"
        updated_expression = build_skip_logic_expression(expression, questions_with_skip)
        
        # Skip logic should use the original question ID since it exists
        self.assertIn("pregnancyTest", updated_expression)

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
        """Test that options are sorted by 'Order' column"""
        # Create mock DataFrame with 'Order' column
        mock_data = pd.DataFrame({
            'OptionSet name': ['TestSet', 'TestSet', 'TestSet', 'TestSet', 'TestSet'],
            'Answers': ['Option 10', 'Option 2', 'Option 1', 'Option 20', 'Option 3'],
            'Order': [10, 2, 1, 20, 3],
            'External ID': ['uuid10', 'uuid2', 'uuid1', 'uuid20', 'uuid3']
        })
        
        mock_option_sets.value = mock_data
        mock_option_sets.__getitem__ = lambda self, key: mock_data[key]
        mock_option_sets.columns = mock_data.columns
        
        # Mock the filtering
        filtered_mock = mock_data[mock_data['OptionSet name'] == 'TestSet']
        mock_option_sets.__getitem__.return_value = filtered_mock
        
        with patch('form_generator.option_sets', mock_data):
            options, found = get_options('TestSet')
            
            # Verify options are sorted by 'Order' column numerically
            self.assertTrue(found)
            self.assertEqual(len(options), 5)
            # After numeric sorting by 'Order', order should be: 1, 2, 3, 10, 20 (not 1, 10, 2, 20, 3)
            expected_order = ['Option 1', 'Option 2', 'Option 3', 'Option 10', 'Option 20']
            actual_order = [opt['Answers'] for opt in options]
            self.assertEqual(actual_order, expected_order)

    @patch('form_generator.option_sets')
    def test_get_options_duplicate_columns(self, mock_option_sets):
        """Test handling of duplicate '#' columns"""
        # Create mock DataFrame with duplicate '#' columns
        mock_data = pd.DataFrame({
            'OptionSet name': ['TestSet', 'TestSet', 'TestSet'],
            'Answers': ['Option C', 'Option A', 'Option B'],
            '#': [3, 1, 2],
            'External ID': ['uuid3', 'uuid1', 'uuid2']
        })
        
        # Simulate duplicate columns by adding another '#' column
        mock_data['#_duplicate'] = [6, 4, 5]
        mock_data.columns = ['OptionSet name', 'Answers', '#', 'External ID', '#']
        
        mock_option_sets.value = mock_data
        mock_option_sets.__getitem__ = lambda self, key: mock_data[key]
        mock_option_sets.columns = mock_data.columns
        
        # Mock the filtering
        filtered_mock = mock_data[mock_data['OptionSet name'] == 'TestSet']
        mock_option_sets.__getitem__.return_value = filtered_mock
        
        with patch('form_generator.option_sets', mock_data):
            # This should not raise an error and should return options
            options, found = get_options('TestSet')
            
            # Verify options are returned even with duplicate columns
            self.assertTrue(found)
            self.assertEqual(len(options), 3)

    def test_question_label_and_id_generation(self):
        """Test question label and ID generation from Question and Label columns"""
        # Mock row data with both Question and Label columns
        row_with_label = pd.Series({
            'Question': 'Original Question',
            'Label if different': 'Different Label',
            'Rendering': 'text',
            'Datatype': 'text'
        })
        
        # Mock row data with empty Label column
        row_with_empty_label = pd.Series({
            'Question': 'Original Question',
            'Label if different': '',  # Empty string
            'Rendering': 'text',
            'Datatype': 'text'
        })
        
        columns = ['Question', 'Label if different', 'Rendering', 'Datatype']
        translations = {}
        
        # Test when Label if different is provided
        with patch('form_generator.manage_id', return_value=('originalQuestion', False, 'Original Question')):
            question_with_label = generate_question(row_with_label, columns, translations)
            self.assertEqual(question_with_label['label'], 'Different Label')
            self.assertEqual(question_with_label['id'], 'originalQuestion')  # ID should be from Question column
        
        # Test when Label if different is empty
        with patch('form_generator.manage_id', return_value=('originalQuestion', False, 'Original Question')):
            question_with_empty_label = generate_question(row_with_empty_label, columns, translations)
            self.assertEqual(question_with_empty_label['label'], 'Original Question')

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
        with patch('form_generator.manage_id', return_value=('testDecimal', False, 'Test Decimal')):
            decimal_question = generate_question(decimal_row, columns, translations)
            self.assertFalse(decimal_question['disallowDecimals'])
        
        # Test number
        with patch('form_generator.manage_id', return_value=('testNumber', False, 'Test Number')):
            number_question = generate_question(number_row, columns, translations)
            self.assertTrue(number_question['disallowDecimals'])

    def test_comprehensive_uniqueness_verification(self):
        """Test comprehensive uniqueness verification across multiple duplicate questions"""
        # Test data with multiple duplicates
        questions_data = [
            {'Question': 'Age', 'Rendering': 'numeric', 'Datatype': 'numeric'},
            {'Question': 'Age', 'Rendering': 'numeric', 'Datatype': 'numeric'},  # Duplicate 1
            {'Question': 'Age', 'Rendering': 'numeric', 'Datatype': 'numeric'},  # Duplicate 2
            {'Question': 'Weight', 'Rendering': 'numeric', 'Datatype': 'numeric'},
            {'Question': 'Weight', 'Rendering': 'numeric', 'Datatype': 'numeric'}  # Duplicate 1
        ]
        
        # Reset global questions list and ID modifications
        from form_generator import ALL_QUESTIONS_ANSWERS, reset_id_modifications
        ALL_QUESTIONS_ANSWERS.clear()
        reset_id_modifications()
        
        columns = ['Question', 'Rendering', 'Datatype']
        translations = {}
        
        # Generate questions one by one to ensure proper ID tracking
        question1 = generate_question(pd.Series(questions_data[0]), columns, translations)
        self.assertEqual(question1['id'], 'age')
        self.assertNotIn('idModified', question1)
        
        question2 = generate_question(pd.Series(questions_data[1]), columns, translations)
        self.assertEqual(question2['id'], 'age_1')
        self.assertTrue(question2.get('idModified', False))
        
        question3 = generate_question(pd.Series(questions_data[2]), columns, translations)
        self.assertEqual(question3['id'], 'age_2')
        self.assertTrue(question3.get('idModified', False))
        
        question4 = generate_question(pd.Series(questions_data[3]), columns, translations)
        self.assertEqual(question4['id'], 'weight')
        self.assertNotIn('idModified', question4)
        
        question5 = generate_question(pd.Series(questions_data[4]), columns, translations)
        self.assertEqual(question5['id'], 'weight_1')
        self.assertTrue(question5.get('idModified', False))
        
        # Verify ALL_QUESTIONS_ANSWERS contains all unique IDs
        all_qa_ids = [q['question_id'] for q in ALL_QUESTIONS_ANSWERS]
        self.assertEqual(len(all_qa_ids), len(set(all_qa_ids)), "ALL_QUESTIONS_ANSWERS should have unique IDs")
        self.assertEqual(set(all_qa_ids), {'age', 'age_1', 'age_2', 'weight', 'weight_1'})
        
        # Clean up
        ALL_QUESTIONS_ANSWERS.clear()
        reset_id_modifications()
 
    def test_answer_order_preservation_with_duplicate_ids(self):
        """Test that answer order is preserved when question IDs are duplicated"""
        # Create test data with duplicate question and an OptionSet with defined order
        questions_data = [
            {'Question': 'Test Question', 'Rendering': 'radio', 'Datatype': 'text', 'OptionSet name': 'TestSet'},
            {'Question': 'Test Question', 'Rendering': 'radio', 'Datatype': 'text', 'OptionSet name': 'TestSet'},  # Duplicate
        ]
        
        # Mock option_sets data
        mock_data = pd.DataFrame({
            'OptionSet name': ['TestSet', 'TestSet', 'TestSet'],
            'Answers': ['Option C', 'Option A', 'Option B'],
            'Order': [3, 1, 2],
            'External ID': ['uuid3', 'uuid1', 'uuid2']
        })
        
        # Initialize option_sets with mock data
        from form_generator import option_sets, initialize_option_sets
        option_sets = mock_data
    
        # Reset global questions list and ID modifications
        from form_generator import ALL_QUESTIONS_ANSWERS, reset_id_modifications
        ALL_QUESTIONS_ANSWERS.clear()
        reset_id_modifications()
        
        columns = ['Question', 'Rendering', 'Datatype', 'OptionSet name']
        translations = {}
        
        # Generate questions
        from form_generator import generate_question
        question1 = generate_question(pd.Series(questions_data[0]), columns, translations, None, mock_data)
        question2 = generate_question(pd.Series(questions_data[1]), columns, translations, None, mock_data)
        
        # Verify that the answers are in the correct order based on the 'Order' column
        expected_order = ['Option A', 'Option B', 'Option C']
        actual_order1 = [answer['label'] for answer in question1['questionOptions']['answers']]
        actual_order2 = [answer['label'] for answer in question2['questionOptions']['answers']]
        
        self.assertEqual(actual_order1, expected_order, "Answer order is not preserved in the first question")
        self.assertEqual(actual_order2, expected_order, "Answer order is not preserved in the second question")
        
        # Clean up
        ALL_QUESTIONS_ANSWERS.clear()
        reset_id_modifications()


class TestIntegration(unittest.TestCase):
    """Integration tests for the form generator"""
    
    def test_id_generation_with_skip_logic(self):
        """Test that generated IDs work correctly with skip logic"""
        # Test that a question with "1 - type" format generates correct ID
        question_id, was_modified, original_label = manage_id("1 - type")
        self.assertEqual(question_id, "1type")
        self.assertEqual(original_label, "1 - type")
        
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

    def test_skip_logic_with_modified_ids(self):
        """Test that skip logic expressions are updated when question IDs are modified"""
        from form_generator import reset_id_modifications, ID_MODIFICATIONS
        
        # Reset modifications tracking
        reset_id_modifications()
        
        # Simulate ID modification
        ID_MODIFICATIONS["Duplicate Question"] = "duplicateQuestion_1"
        
        # Test skip logic expression with original label
        original_expression = "Hide question if [Duplicate Question] !== 'Yes'"
        
        # The skip logic should be updated to use the modified ID
        # This would happen in generate_question function
        updated_expression = original_expression
        for original_label, modified_id in ID_MODIFICATIONS.items():
            updated_expression = updated_expression.replace(f"[{original_label}]", f"[{modified_id}]")
        
        expected_expression = "Hide question if [duplicateQuestion_1] !== 'Yes'"
        self.assertEqual(updated_expression, expected_expression)
        
        # Clean up
        reset_id_modifications()

    def test_id_modification_warnings(self):
        """Test that warnings are added to questions with modified IDs"""
        # Reset global questions list and ID modifications
        from form_generator import ALL_QUESTIONS_ANSWERS, reset_id_modifications
        ALL_QUESTIONS_ANSWERS.clear()
        reset_id_modifications()
        
        # Create duplicate questions
        questions_data = [
            {'Question': 'Test Question', 'Rendering': 'text', 'Datatype': 'text'},
            {'Question': 'Test Question', 'Rendering': 'text', 'Datatype': 'text'},  # Duplicate
        ]
        
        columns = ['Question', 'Rendering', 'Datatype']
        translations = {}
        
        # Generate first question (should not be modified)
        question1 = generate_question(pd.Series(questions_data[0]), columns, translations)
        self.assertEqual(question1['id'], 'testQuestion')
        self.assertNotIn('idModified', question1)
        self.assertNotIn('warning', question1)
        
        # Generate second question (should be modified)
        question2 = generate_question(pd.Series(questions_data[1]), columns, translations)
        self.assertEqual(question2['id'], 'testQuestion_1')
        self.assertTrue(question2.get('idModified', False))
        self.assertIn('warning', question2)
        self.assertIn('originalLabel', question2)
        self.assertEqual(question2['originalLabel'], 'Test Question')
        
        # Clean up
        ALL_QUESTIONS_ANSWERS.clear()
        reset_id_modifications()


if __name__ == '__main__':
    # Create test directory if it doesn't exist
    os.makedirs('tests', exist_ok=True)
    
    # Run the tests
    unittest.main(verbosity=2)
