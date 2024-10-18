import os
import requests
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the blueprint
gemini_bp = Blueprint('gemini', __name__, url_prefix='/gemini')

# Get the API key from the environment
gemini_api_key = os.getenv('GEMINI_API_KEY')

@gemini_bp.route('/generate-content', methods=['POST'])
def generate_content():
    if not gemini_api_key:
        return jsonify({'error': 'GEMINI_API_KEY not configured'}), 500
    
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Missing prompt in request body'}), 400
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    api_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}'
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": data['prompt']}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        # Extract the main content and metadata
        if 'candidates' in response_data and response_data['candidates']:
            candidate = response_data['candidates'][0]
            
            # Extract useful information
            result = {
                'content': candidate['content']['parts'][0]['text'],
                'finish_reason': candidate['finishReason'],
                'safety_ratings': {
                    rating['category']: rating['probability']
                    for rating in candidate['safetyRatings']
                },
                'usage': {
                    'prompt_tokens': response_data['usageMetadata']['promptTokenCount'],
                    'response_tokens': response_data['usageMetadata']['candidatesTokenCount'],
                    'total_tokens': response_data['usageMetadata']['totalTokenCount']
                }
            }
            
            return jsonify(result)
        
        return jsonify({'error': 'No content generated'}), 500
        
    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if response is not None:
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', str(e))
            except:
                pass
        return jsonify({
            'error': 'Failed to generate content',
            'details': error_message
        }), response.status_code if response is not None else 500