#!/usr/bin/env python3
"""
Demo script to showcase the enhanced question ID uniqueness verification functionality.
"""

import sys
import os
import pandas as pd

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from form_generator import (
    generate_question,
    ALL_QUESTIONS_ANSWERS,
    reset_id_modifications,
    ID_MODIFICATIONS
)

def demo_uniqueness_verification():
    """Demonstrate the enhanced question ID uniqueness verification."""
    
    print("=== Enhanced Question ID Uniqueness Verification Demo ===\n")
    
    # Reset global state
    ALL_QUESTIONS_ANSWERS.clear()
    reset_id_modifications()
    
    # Create test data with duplicate questions
    test_questions = [
        {'Question': 'Patient Age', 'Rendering': 'numeric', 'Datatype': 'numeric'},
        {'Question': 'Patient Age', 'Rendering': 'numeric', 'Datatype': 'numeric'},  # Duplicate 1
        {'Question': 'Patient Age', 'Rendering': 'numeric', 'Datatype': 'numeric'},  # Duplicate 2
        {'Question': 'Weight (kg)', 'Rendering': 'numeric', 'Datatype': 'numeric'},
        {'Question': 'Weight (kg)', 'Rendering': 'numeric', 'Datatype': 'numeric'},  # Duplicate 1
        {'Question': '1 - Type of Visit', 'Rendering': 'radio', 'Datatype': 'coded'},
        {'Question': '1 - Type of Visit', 'Rendering': 'radio', 'Datatype': 'coded'},  # Duplicate 1
    ]
    
    columns = ['Question', 'Rendering', 'Datatype']
    translations = {}
    
    print("Generating questions with duplicate detection:\n")
    
    generated_questions = []
    for i, question_data in enumerate(test_questions):
        print(f"Processing question {i+1}: '{question_data['Question']}'")
        
        question = generate_question(pd.Series(question_data), columns, translations)
        generated_questions.append(question)
        
        print(f"  Generated ID: '{question['id']}'")
        
        if question.get('idModified', False):
            print(f"  ⚠️  WARNING: ID was modified for uniqueness")
            print(f"  Original label: '{question['originalLabel']}'")
            print(f"  Warning message: {question['warning']}")
        else:
            print(f"  ✅ ID is unique")
        
        print()
    
    print("=== Summary ===")
    print(f"Total questions processed: {len(test_questions)}")
    print(f"Unique IDs generated: {len(set(q['id'] for q in generated_questions))}")
    print(f"Questions with modified IDs: {sum(1 for q in generated_questions if q.get('idModified', False))}")
    
    print("\n=== All Generated Question IDs ===")
    for i, question in enumerate(generated_questions):
        status = "MODIFIED" if question.get('idModified', False) else "ORIGINAL"
        print(f"{i+1}. '{question['id']}' ({status})")
    
    print("\n=== ID Modifications Tracking ===")
    if ID_MODIFICATIONS:
        for original, modified in ID_MODIFICATIONS.items():
            print(f"'{original}' → '{modified}'")
    else:
        print("No ID modifications were tracked.")
    
    print("\n=== ALL_QUESTIONS_ANSWERS Verification ===")
    all_ids = [qa['question_id'] for qa in ALL_QUESTIONS_ANSWERS]
    unique_ids = set(all_ids)
    print(f"Total entries: {len(all_ids)}")
    print(f"Unique IDs: {len(unique_ids)}")
    print(f"Duplicates detected: {'No' if len(all_ids) == len(unique_ids) else 'Yes'}")
    
    # Clean up
    ALL_QUESTIONS_ANSWERS.clear()
    reset_id_modifications()
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    demo_uniqueness_verification()
