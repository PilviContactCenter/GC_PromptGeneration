# 🎙️ Prompt Studio

**Create professional audio prompts for your Genesys Cloud contact center in minutes, not hours.**

Prompt Studio is a web application that streamlines the creation and management of IVR audio prompts. Whether you need to generate text-to-speech messages, record your own voice, or upload existing audio files — Prompt Studio handles it all and exports directly to Genesys Cloud.

---

## 🎯 Why Prompt Studio?

Managing IVR prompts in a contact center can be time-consuming:

- Recording prompts requires coordination with voice talent
- Updating a single word means re-recording the entire message
- Uploading files to Genesys Cloud involves multiple steps
- Keeping track of prompt versions is challenging

**Prompt Studio solves these problems by providing a single, intuitive interface for all your prompt needs.**

---

## 🔄 How It Works

```mermaid
flowchart LR
    subgraph Input["📥 Create Your Prompt"]
        A[/"Text to Speech"/]
        B[/"Record Voice"/]
        C[/"Upload File"/]
    end
    
    subgraph Process["⚙️ Prompt Studio"]
        D["Preview & Edit"]
        E["Select Language"]
    end
    
    subgraph Output["📤 Deploy"]
        F[("Genesys Cloud\nArchitect")]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    
    style A fill:#ff4f1f,color:#fff
    style B fill:#ff4f1f,color:#fff
    style C fill:#ff4f1f,color:#fff
    style F fill:#1b3d6f,color:#fff
```

---

## ✨ Key Features

### 🗣️ Text-to-Speech Generation
Convert written text into natural-sounding audio using Azure's Neural voices. Perfect for:
- Quick prompt updates
- Multi-language support
- Consistent voice quality across all prompts

### 🎤 Voice Recording
Record directly in your browser — no external software needed. Ideal for:
- Personal greetings
- Custom announcements
- Brand-specific voice requirements

### 📁 File Import
Upload existing WAV files from your computer or professional recording studio.

### ☁️ One-Click Export
Send your finished prompt directly to Genesys Cloud Architect with a single click. No more manual file uploads!

---

## 👥 User Journey

```mermaid
journey
    title Creating a New IVR Prompt
    section Login
      Open Prompt Studio: 5: User
      Sign in with Genesys Cloud: 5: User
    section Create
      Choose creation method: 5: User
      Enter text or record audio: 4: User
      Preview the prompt: 5: User
    section Export
      Enter prompt name: 5: User
      Select language: 5: User
      Export to Genesys Cloud: 5: User
    section Done
      Prompt available in Architect: 5: System
```

---

## 🏗️ Architecture Overview

```mermaid
flowchart TB
    subgraph Client["🖥️ Web Browser"]
        UI["Prompt Studio UI"]
        REC["Audio Recorder"]
        WAVE["Waveform Player"]
    end
    
    subgraph Server["🖧 Flask Application"]
        AUTH["OAuth Handler"]
        TTS["TTS Service"]
        EXP["Export Service"]
        DB[("SQLite DB")]
    end
    
    subgraph External["☁️ Cloud Services"]
        GC["Genesys Cloud"]
        AZURE["Azure Speech"]
    end
    
    UI --> AUTH
    UI --> TTS
    UI --> EXP
    REC --> UI
    WAVE --> UI
    
    AUTH <--> GC
    TTS <--> AZURE
    EXP <--> GC
    AUTH --> DB
    
    style GC fill:#1b3d6f,color:#fff
    style AZURE fill:#0078d4,color:#fff
    style UI fill:#ff4f1f,color:#fff
```

---

## 🔐 Authentication Flow

Prompt Studio supports two authentication modes:

### Standalone Mode (Browser)
When accessed directly in a web browser, users sign in via Genesys Cloud OAuth.

### Embedded Mode (Genesys Cloud)
When embedded as a Client App within Genesys Cloud, authentication is automatic — no login required!

```mermaid
flowchart TD
    A[User Opens App] --> B{Embedded in\nGenesys Cloud?}
    
    B -->|Yes| C[Detect iframe]
    C --> D[Get token from\nPlatform SDK]
    D --> E[Auto-authenticate]
    
    B -->|No| F[Show login page]
    F --> G[Redirect to\nGenesys Cloud]
    G --> H[User logs in]
    H --> I[Redirect back\nwith token]
    
    E --> J[Access Prompt Studio]
    I --> J
    
    style J fill:#1fa343,color:#fff
    style E fill:#1b3d6f,color:#fff
    style I fill:#1b3d6f,color:#fff
```

### 📸 Embedded Mode Preview

Here's how Prompt Studio looks when embedded as a Client App inside Genesys Cloud:

<p align="center">
  <img src="screenshots/embedded-mode.png" alt="Prompt Studio embedded in Genesys Cloud" width="800" />
</p>

*Seamlessly integrated with the Genesys Cloud interface — users can create and manage prompts without leaving their workspace!*

---

## 🌍 Supported Languages

Export prompts in any language supported by Genesys Cloud:

| Language | Code | Language | Code |
|----------|------|----------|------|
| English (US) | `en-us` | German | `de-de` |
| English (UK) | `en-gb` | French | `fr-fr` |
| Spanish | `es-es` | Italian | `it-it` |
| Portuguese | `pt-br` | Dutch | `nl-nl` |
| Polish | `pl-pl` | Japanese | `ja-jp` |

*...and many more!*

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Azure Cognitive Services account (for Text-to-Speech)
- Genesys Cloud organization with:
  - OAuth Client (Authorization Code) for user login
  - OAuth Client (Client Credentials) for API operations
  - Architect permissions

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/PromptGeneration.git
   cd PromptGeneration
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://localhost:5001
   ```

---

## 🐳 Docker Deployment

For production deployments, we recommend using Docker.

### Quick Start with Docker Compose

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Build and run**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   ```
   http://localhost:5001
   ```

### Docker Commands

```bash
# Build the image
docker build -t prompt-studio .

# Run the container
docker run -d \
  --name prompt-studio \
  -p 5001:5001 \
  --env-file .env \
  -v $(pwd)/uploads:/app/uploads \
  prompt-studio

# View logs
docker logs -f prompt-studio

# Stop the container
docker-compose down
```

### Production Deployment

For production, consider:
- Using a reverse proxy (nginx) for HTTPS
- Setting `OAUTH_REDIRECT_URI` to your production URL
- Using a persistent volume for uploads
- Configuring proper security headers

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `AZURE_SPEECH_KEY` | Your Azure Speech Services API key |
| `AZURE_SPEECH_REGION` | Azure region (e.g., `westeurope`) |
| `GENESYS_CLIENT_ID` | Client Credentials OAuth client ID |
| `GENESYS_CLIENT_SECRET` | Client Credentials OAuth client secret |
| `OAUTH_CLIENT_ID` | Authorization Code OAuth client ID |
| `OAUTH_CLIENT_SECRET` | Authorization Code OAuth client secret |
| `GENESYS_BASE_URL` | Genesys Cloud region (e.g., `mypurecloud.de`) |

---

## 📂 Project Structure

```
PromptGeneration/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── models.py              # Database models
├── services/
│   ├── azure_tts.py       # Azure Text-to-Speech integration
│   └── genesys_export.py  # Genesys Cloud Architect export
├── static/
│   ├── css/spark.css      # Genesys Spark design system
│   └── js/main.js         # Frontend JavaScript
├── templates/
│   ├── index.html         # Main application page
│   └── login.html         # OAuth login page
└── uploads/               # Temporary audio file storage
```

---

## 🎨 Design

Prompt Studio follows the **Genesys Spark Design System**, ensuring a consistent look and feel with other Genesys Cloud applications.

---

## 📜 License

MIT License

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## ☕ Support This Project

Building tools like Prompt Studio takes countless hours of coding, debugging, and drinking coffee. ☕

If this project saved you time or made your life easier, consider buying me a coffee! Your support helps keep the development going and the coffee pot full.

<p align="center">
  <a href="https://ko-fi.com/pilvi_pl" target="_blank">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Buy Me a Coffee at ko-fi.com" />
  </a>
</p>

**Every coffee counts!** Whether it's a single espresso or a fancy latte, your contribution means the world. 🙏

---

<p align="center">
  <strong>Powered by Pilvi</strong><br>
  <em>Making contact center management simpler</em>
</p>
