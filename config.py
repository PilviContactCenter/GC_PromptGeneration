import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    # App secret
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # File uploads
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///promptstudio.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Azure TTS Credentials
    AZURE_SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY')
    AZURE_SPEECH_REGION = os.getenv('AZURE_SPEECH_REGION')
    
    # Genesys Cloud API Credentials (for Client Credentials exports)
    GENESYS_CLIENT_ID = os.getenv('GENESYS_CLIENT_ID')
    GENESYS_CLIENT_SECRET = os.getenv('GENESYS_CLIENT_SECRET')
    GENESYS_REGION = os.getenv('GENESYS_REGION', 'mypurecloud.de')
    
    # Genesys Cloud OAuth (for User Login)
    OAUTH_CLIENT_ID = os.getenv('OAUTH_CLIENT_ID')
    OAUTH_CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET')
    OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5001/oauth/callback')
    GENESYS_BASE_URL = os.getenv('GENESYS_BASE_URL', 'mypurecloud.de')
