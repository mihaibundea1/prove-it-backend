import json
from datetime import datetime
from flask import current_app

file_path = 'data/questions.json'  

def load_questions_from_file():
    with open(file_path, 'r') as file:
        questions = json.load(file)
    return questions

def update_questions():
    new_questions = load_questions_from_file()

    questions_collection = current_app.db_content.questions

    latest_version = questions_collection.find_one(sort=[("version", -1)])
    new_version = (latest_version['version'] + 1) if latest_version else 1

    versioned_questions = {
        "version": new_version,
        "date": datetime.now(),
        "questions": new_questions
    }

    questions_collection.insert_one(versioned_questions)

    return f"Questions updated to version {new_version}"
