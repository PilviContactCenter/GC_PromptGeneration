"""
Prompt Studio - Genesys Cloud Audio Prompt Generator
Features: Text-to-Speech, Audio Recording, File Import, Export to Genesys Cloud
With Genesys Cloud OAuth Authentication (Standalone + Embedded Mode)

Simplified architecture: Session-based authentication (no database required)
"""
from flask import Flask, redirect, url_for, render_template, request, session, jsonify, send_from_directory
from functools import wraps
from config import Config
import os
import re
import uuid
import secrets
import base64
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# OAuth Configuration for Genesys Cloud (loaded from Config)
OAUTH_CONFIG = {
    'client_id': Config.OAUTH_CLIENT_ID,
    'client_secret': Config.OAUTH_CLIENT_SECRET,
    'redirect_uri': Config.OAUTH_REDIRECT_URI,
    'base_url': Config.GENESYS_BASE_URL,
    'scopes': 'architect users:readonly'
}


def login_required(f):
    """Custom decorator to check if user is authenticated via session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_info' not in session or not session.get('access_token'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def sanitize_prompt_name(name):
    """Sanitize prompt name to only contain letters, numbers, and underscores.
    Must start with a letter (not a number)."""
    name = name.replace('-', '_')
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    # Genesys requires names to start with a letter, not a number
    if name and not name[0].isalpha():
        name = 'P_' + name
    return name if name else 'Prompt'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Import services here to avoid circular imports
    from services.azure_tts import generate_speech
    from services.genesys_export import upload_prompt_to_genesys
    
    # ============== OAUTH ROUTES ==============
    
    @app.route('/login')
    def login():
        """Show login page."""
        if 'user_info' in session and session.get('access_token'):
            return redirect(url_for('index'))
        return render_template('login.html', config=app.config)
    
    @app.route('/oauth/authorize')
    def oauth_authorize():
        """Redirect to Genesys Cloud OAuth login."""
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        auth_url = (
            f"https://login.{OAUTH_CONFIG['base_url']}/oauth/authorize"
            f"?client_id={OAUTH_CONFIG['client_id']}"
            f"&response_type=code"
            f"&redirect_uri={OAUTH_CONFIG['redirect_uri']}"
            f"&scope={OAUTH_CONFIG['scopes']}"
            f"&state={state}"
        )
        
        return redirect(auth_url)
    
    @app.route('/oauth/callback')
    def oauth_callback():
        """Handle OAuth callback from Genesys Cloud."""
        # Check for errors
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', 'Unknown error')
            return render_template('login.html', error=f"Login failed: {error_description}", config=app.config)
        
        # Verify state (lenient for embedded mode)
        state = request.args.get('state')
        stored_state = session.get('oauth_state')
        if stored_state and state != stored_state:
            return render_template('login.html', error="Invalid state parameter. Please try again.", config=app.config)
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            return render_template('login.html', error="No authorization code received.", config=app.config)
        
        # Exchange code for access token
        token_url = f"https://login.{OAUTH_CONFIG['base_url']}/oauth/token"
        
        credentials = f"{OAUTH_CONFIG['client_id']}:{OAUTH_CONFIG['client_secret']}"
        credentials_encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {credentials_encoded}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': OAUTH_CONFIG['redirect_uri']
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data)
            
            if response.status_code != 200:
                return render_template('login.html', error=f"Token exchange failed: {response.text}", config=app.config)
            
            token_data = response.json()
            
            # Store tokens in session
            session['access_token'] = token_data['access_token']
            session['token_expires'] = time.time() + token_data.get('expires_in', 3600)
            
            if 'refresh_token' in token_data:
                session['refresh_token'] = token_data['refresh_token']
            
            # Get user info from Genesys Cloud
            user_response = requests.get(
                f"https://api.{OAUTH_CONFIG['base_url']}/api/v2/users/me",
                headers={'Authorization': f"Bearer {token_data['access_token']}"},
                verify=False
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                
                # Store user info in session
                session['user_info'] = {
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'username': user_data.get('username')
                }
            
            return redirect(url_for('index'))
        
        except Exception as e:
            return render_template('login.html', error=f"Authentication error: {str(e)}", config=app.config)
    
    # ============== EMBEDDED MODE AUTHENTICATION ==============
    
    @app.route('/auth/embedded', methods=['POST'])
    def auth_embedded():
        """
        Handle authentication from embedded mode (Genesys Cloud iframe).
        Receives access token from the Platform SDK and creates a session.
        """
        try:
            data = request.get_json()
            access_token = data.get('access_token')
            
            if not access_token:
                return jsonify({'success': False, 'error': 'No access token provided'}), 400
            
            # Validate the token by fetching user info from Genesys Cloud
            user_response = requests.get(
                f"https://api.{OAUTH_CONFIG['base_url']}/api/v2/users/me",
                headers={'Authorization': f"Bearer {access_token}"},
                verify=False
            )
            
            if user_response.status_code != 200:
                return jsonify({
                    'success': False, 
                    'error': f'Token validation failed: {user_response.status_code}'
                }), 401
            
            user_data = user_response.json()
            
            # Store tokens in session
            session['access_token'] = access_token
            session['token_expires'] = time.time() + 3600
            session['embedded_mode'] = True
            
            # Store user info in session
            session['user_info'] = {
                'id': user_data.get('id'),
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'username': user_data.get('username')
            }
            
            return jsonify({
                'success': True,
                'user': {
                    'name': user_data.get('name'),
                    'email': user_data.get('email')
                }
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/logout')
    @login_required
    def logout():
        """Log out user."""
        session.clear()
        return redirect(url_for('login'))
    
    # ============== MAIN ROUTES ==============
    
    @app.route('/')
    @login_required
    def index():
        """Main prompt studio page."""
        user_info = session.get('user_info', {})
        return render_template('index.html', user=user_info, config=app.config)
    
    # ============== API ROUTES ==============
    
    @app.route('/api/tts', methods=['POST'])
    @login_required
    def tts_generate():
        data = request.json
        text = data.get('text')
        voice = data.get('voice', 'en-US-JennyNeural')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        filename = f"tts_{uuid.uuid4().hex[:16]}.wav"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            success = generate_speech(text, filepath, voice)
            if success:
                return jsonify({'success': True, 'filename': filename, 'url': f'/uploads/{filename}'})
            else:
                return jsonify({'error': 'TTS Generation failed'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/upload', methods=['POST'])
    @login_required
    def upload_file():
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file:
            ext = os.path.splitext(file.filename)[1]
            filename = f"upload_{uuid.uuid4().hex[:16]}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            return jsonify({'success': True, 'filename': filename, 'url': f'/uploads/{filename}'})

    @app.route('/api/export', methods=['POST'])
    @login_required
    def export_genesys():
        data = request.json
        filename = data.get('filename')
        prompt_name = sanitize_prompt_name(data.get('promptName', ''))
        description = data.get('description', '')
        language = data.get('language', 'en-us')

        if not filename or not prompt_name:
            return jsonify({'error': 'Missing filename or prompt name'}), 400

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404

        try:
            upload_prompt_to_genesys(filepath, prompt_name, description, language)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/uploads/<filename>')
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=5001)
