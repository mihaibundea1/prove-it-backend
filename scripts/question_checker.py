# scripts/question_checker.py
from flask import current_app

def check_question_changes():
    # Get the latest and previous version of questions
    questions_collection = current_app.db_content.questions
    latest_version = questions_collection.find_one(sort=[("version", -1)])
    previous_version = questions_collection.find_one(
        {"version": latest_version['version'] - 1}
    )

    if not previous_version:
        return "No previous version to compare."

    latest_questions = {q['id']: q for q in latest_version['questions']}
    previous_questions = {q['id']: q for q in previous_version['questions']}

    changes = {
        "added": [],
        "removed": [],
        "modified": []
    }

    # Check for added and modified questions
    for q_id, latest_question in latest_questions.items():
        if q_id not in previous_questions:
            changes["added"].append(latest_question)
        else:
            # Compare the questions for modifications
            previous_question = previous_questions[q_id]
            if latest_question != previous_question:
                changes["modified"].append({
                    "previous": previous_question,
                    "latest": latest_question
                })

    # Check for removed questions
    for q_id in previous_questions:
        if q_id not in latest_questions:
            changes["removed"].append(previous_questions[q_id])

    return changes
