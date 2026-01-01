# Prompt Studio

A web-based application for creating, recording, and managing audio prompts for Genesys Cloud contact centers.

## Features

- **Text-to-Speech**: Generate audio prompts using Azure Cognitive Services
- **Voice Recording**: Record audio directly in the browser
- **File Import**: Upload existing WAV files
- **Genesys Cloud Export**: Upload prompts directly to Genesys Cloud Architect
- **Multi-language Support**: Select language codes for prompts (en-us, de-de, fr-fr, etc.)
- **Genesys Cloud Authentication**: 
  - **Standalone Mode**: OAuth login via browser redirect
  - **Embedded Mode**: Automatic authentication when embedded in Genesys Cloud

## Prerequisites

- Python 3.9+
- Azure Cognitive Services Speech subscription
- Genesys Cloud account with:
  - OAuth Client (Authorization Code Grant) for user login
  - OAuth Client (Client Credentials Grant) for API operations
  - Architect permissions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/PromptGeneration.git
cd PromptGeneration
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (copy `.env.example` to `.env`):
```env
# Azure TTS
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=westeurope

# Genesys API Credentials (Client Credentials Grant - for exports)
GENESYS_CLIENT_ID=your-client-id
GENESYS_CLIENT_SECRET=your-client-secret
GENESYS_REGION=mypurecloud.de

# Genesys OAuth (Authorization Code Grant - for user login)
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
OAUTH_REDIRECT_URI=http://localhost:5001/oauth/callback
GENESYS_BASE_URL=mypurecloud.de

# App Secret Key
SECRET_KEY=your-random-secret-key
```

4. Run the application:
```bash
python app.py
```

5. Open http://localhost:5001 in your browser

## Genesys Cloud Setup

### OAuth Client for User Login (Authorization Code Grant)

1. Go to Admin > Integrations > OAuth
2. Create a new OAuth client:
   - **Grant Type**: Authorization Code
   - **Authorized Redirect URIs**: `http://localhost:5001/oauth/callback`
   - **Scope**: `architect`, `users:readonly`

### OAuth Client for API Operations (Client Credentials Grant)

1. Create another OAuth client:
   - **Grant Type**: Client Credentials
   - **Roles**: Assign a role with Architect permissions

## Embedded Mode (Genesys Cloud Client App)

When this application is embedded as a Client App within Genesys Cloud:

1. The app automatically detects the iframe environment
2. Uses the Genesys Cloud Platform SDK to obtain the access token
3. No separate login is required - inherits the user's Genesys Cloud session

### Client App Configuration

1. Go to Admin > Integrations > Integrations
2. Add new Integration > Client Application
3. Configure:
   - **Application URL**: Your deployed application URL
   - **iFrame Sandbox Options**: Enable as needed
   - **Permissions**: Architect access

## Project Structure

```
PromptGeneration/
├── app.py                  # Main Flask application with OAuth
├── config.py               # Configuration settings
├── extensions.py           # Flask extensions (SQLAlchemy)
├── models.py               # Database models (AuthUser)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── services/
│   ├── azure_tts.py        # Azure TTS integration
│   └── genesys_export.py   # Genesys Cloud Architect export
├── static/
│   ├── css/
│   │   └── spark.css       # Genesys Spark design system
│   └── js/
│       └── main.js         # Frontend JavaScript
├── templates/
│   ├── index.html          # Main application page
│   └── login.html          # OAuth login page
└── uploads/                # Temporary audio file storage
```

## Technologies

- **Backend**: Flask, Flask-Login, Flask-SQLAlchemy
- **Frontend**: HTML5, CSS3 (Genesys Spark Design System), JavaScript
- **TTS**: Azure Cognitive Services Speech SDK
- **API**: Genesys Cloud Platform SDK
- **Audio**: Wavesurfer.js for waveform visualization

## License

MIT License

---

Powered by **Pilvi**
