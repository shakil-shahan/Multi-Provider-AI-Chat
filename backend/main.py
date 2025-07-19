from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# API endpoints for different providers
API_CONFIGS = {
    'openai': {
        'url': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-3.5-turbo'
    },
    'anthropic': {
        'url': 'https://api.anthropic.com/v1/messages',
        'model': 'claude-3-haiku-20240307'
    },
    'huggingface': {
        'url': 'https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium',
        'model': 'microsoft/DialoGPT-medium'
    },
    'cohere': {
        'url': 'https://api.cohere.ai/v1/generate',
        'model': 'command'
    }
}


@app.route('/')
def home():
    return jsonify({
        "message": "Multi-Provider Chat API Server is running!",
        "supported_providers": list(API_CONFIGS.keys())
    })


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        provider = data.get('provider', 'openai').lower()
        api_key = request.headers.get('X-API-Key')

        # Validation
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        if not api_key:
            return jsonify({'error': 'API key is required in headers'}), 400

        if provider not in API_CONFIGS:
            return jsonify({'error': f'Unsupported provider: {provider}'}), 400

        # Call the appropriate API
        if provider == 'openai':
            response = call_openai_api(user_message, api_key)
        elif provider == 'anthropic':
            response = call_anthropic_api(user_message, api_key)
        elif provider == 'huggingface':
            response = call_huggingface_api(user_message, api_key)
        elif provider == 'cohere':
            response = call_cohere_api(user_message, api_key)
        else:
            return jsonify({'error': 'Provider not implemented'}), 400

        return jsonify({
            'response': response,
            'provider': provider,
            'model': API_CONFIGS[provider]['model']
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


def call_openai_api(message, api_key):
    """Call OpenAI GPT API"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': API_CONFIGS['openai']['model'],
        'messages': [{'role': 'user', 'content': message}],
        'max_tokens': 1000,
        'temperature': 0.7
    }

    try:
        response = requests.post(API_CONFIGS['openai']['url'],
                                 headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            error_msg = f"OpenAI API Error {response.status_code}"
            if response.status_code == 401:
                error_msg += ": Invalid API key"
            elif response.status_code == 429:
                error_msg += ": Rate limit exceeded"
            else:
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('error', {}).get('message', 'Unknown error')}"
                except:
                    error_msg += f": {response.text[:100]}"
            return error_msg
    except requests.exceptions.Timeout:
        return "Request timeout - please try again"
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"


def call_anthropic_api(message, api_key):
    """Call Anthropic Claude API"""
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }

    payload = {
        'model': API_CONFIGS['anthropic']['model'],
        'max_tokens': 1000,
        'messages': [{'role': 'user', 'content': message}]
    }

    try:
        response = requests.post(API_CONFIGS['anthropic']['url'],
                                 headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return data['content'][0]['text']
        else:
            error_msg = f"Anthropic API Error {response.status_code}"
            if response.status_code == 401:
                error_msg += ": Invalid API key"
            elif response.status_code == 429:
                error_msg += ": Rate limit exceeded"
            else:
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('error', {}).get('message', 'Unknown error')}"
                except:
                    error_msg += f": {response.text[:100]}"
            return error_msg
    except requests.exceptions.Timeout:
        return "Request timeout - please try again"
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"


def call_huggingface_api(message, api_key):
    """Call Hugging Face Inference API"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = {
        'inputs': message,
        'parameters': {
            'max_length': 1000,
            'temperature': 0.7,
            'do_sample': True
        }
    }

    try:
        response = requests.post(API_CONFIGS['huggingface']['url'],
                                 headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                generated_text = data[0].get('generated_text', '')
                # Remove the input message from response if it's included
                if generated_text.startswith(message):
                    generated_text = generated_text[len(message):].strip()
                return generated_text if generated_text else "I understand your message."
            else:
                return "Received unexpected response format"
        else:
            error_msg = f"Hugging Face API Error {response.status_code}"
            if response.status_code == 401:
                error_msg += ": Invalid API key"
            elif response.status_code == 429:
                error_msg += ": Rate limit exceeded"
            elif response.status_code == 503:
                error_msg += ": Model is loading, please try again in a few minutes"
            else:
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('error', 'Unknown error')}"
                except:
                    error_msg += f": {response.text[:100]}"
            return error_msg
    except requests.exceptions.Timeout:
        return "Request timeout - please try again"
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"


def call_cohere_api(message, api_key):
    """Call Cohere API"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': API_CONFIGS['cohere']['model'],
        'prompt': message,
        'max_tokens': 1000,
        'temperature': 0.7,
        'k': 0,
        'stop_sequences': [],
        'return_likelihoods': 'NONE'
    }

    try:
        response = requests.post(API_CONFIGS['cohere']['url'],
                                 headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            generations = data.get('generations', [])
            if generations:
                return generations[0].get('text', '').strip()
            else:
                return "No response generated"
        else:
            error_msg = f"Cohere API Error {response.status_code}"
            if response.status_code == 401:
                error_msg += ": Invalid API key"
            elif response.status_code == 429:
                error_msg += ": Rate limit exceeded"
            else:
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('message', 'Unknown error')}"
                except:
                    error_msg += f": {response.text[:100]}"
            return error_msg
    except requests.exceptions.Timeout:
        return "Request timeout - please try again"
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"


@app.route('/providers', methods=['GET'])
def get_providers():
    """Get list of supported providers and their models"""
    providers = []
    for provider, config in API_CONFIGS.items():
        providers.append({
            'id': provider,
            'name': provider.title(),
            'model': config['model']
        })
    return jsonify({'providers': providers})


if __name__ == '__main__':
    print("Starting Multi-Provider Chat API Server...")
    print("Supported providers:", list(API_CONFIGS.keys()))
    app.run(debug=True, port=5000)
