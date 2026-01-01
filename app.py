"""
Prompt Studio - Genesys Cloud Audio Prompt Generator
Features: Text-to-Speech, Audio Recording, File Import, Export to Genesys Cloud
With Genesys Cloud OAuth Authentication (Standalone + Embedded Mode)
"""
from flask import Flask, redirect, url_for, render_template, request, session, jsonify, send_from_directory
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from extensions import db
from models import AuthUser
import os
import re
import uuid
import secrets
import base64
import time
import requests
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from datetime import datetime

load_dotenv()

login_manager = LoginManager()

# OAuth Configuration for Genesys Cloud
OAUTH_CONFIG = {
    'client_id': os.getenv('OAUTH_CLIENT_ID'),
    'client_secret': os.getenv('OAUTH_CLIENT_SECRET'),
    'redirect_uri': os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5001/oauth/callback'),
    'base_url': os.getenv('GENESYS_BASE_URL', 'mypurecloud.de'),
    'scopes': 'architect users:readonly'
}

# App Configuration
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///promptstudio.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # Azure TTS Credentials
    AZURE_SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY')
    AZURE_SPEECH_REGION = os.getenv('AZURE_SPEECH_REGION')

    # Genesys Cloud API Credentials (for exports)
    GENESYS_CLIENT_ID = os.getenv('GENESYS_CLIENT_ID')
    GENESYS_CLIENT_SECRET = os.getenv('GENESYS_CLIENT_SECRET')
    GENESYS_REGION = os.getenv('GENESYS_REGION', 'mypurecloud.de')
    GENESYS_BASE_URL = OAUTH_CONFIG['base_url']

    # Session cookie settings for embedded iframe support
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True  # Required when SameSite=None (needs HTTPS)


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
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return AuthUser.query.get(int(user_id))
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Import services here to avoid circular imports
    from services.azure_tts import generate_speech
    from services.genesys_export import upload_prompt_to_genesys
    
    # ============== OAUTH ROUTES ==============
    
    @app.route('/login')
    def login():
        """Show login page."""
        if current_user.is_authenticated:
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
                
                # Create or update AuthUser in database for Flask-Login
                auth_user = AuthUser.query.filter_by(email=user_data.get('email')).first()
                if not auth_user:
                    auth_user = AuthUser(
                        email=user_data.get('email'),
                        genesys_user_id=user_data.get('id'),
                        name=user_data.get('name'),
                        password_hash=generate_password_hash(secrets.token_hex(16)),
                        role='user',
                        is_active=True
                    )
                    db.session.add(auth_user)
                else:
                    auth_user.name = user_data.get('name')
                    auth_user.genesys_user_id = user_data.get('id')
                    auth_user.last_login = datetime.utcnow()
                
                db.session.commit()
                
                # Log in the user with Flask-Login
                login_user(auth_user)
            
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
            
            # Create or update AuthUser in database for Flask-Login
            auth_user = AuthUser.query.filter_by(email=user_data.get('email')).first()
            if not auth_user:
                auth_user = AuthUser(
                    email=user_data.get('email'),
                    genesys_user_id=user_data.get('id'),
                    name=user_data.get('name'),
                    password_hash=generate_password_hash(secrets.token_hex(16)),
                    role='user',
                    is_active=True
                )
                db.session.add(auth_user)
            else:
                auth_user.last_login = datetime.utcnow()
            
            db.session.commit()
            
            # Log in the user with Flask-Login
            login_user(auth_user)
            
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
        logout_user()
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
    app.run(debug=True, port=5001)
