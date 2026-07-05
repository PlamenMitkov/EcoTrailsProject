Markdown
# EcoTrailsProject V1: Intelligent Travel Assistant (Bachelor's Diploma Thesis)

Welcome to the foundation of the **EcoTrails** ecosystem. This repository contains the primary release (Version 1) of the EcoTrails system, originally developed and successfully defended as a Bachelor's Thesis project in Computer Systems and Technology at the University of Ruse.

The project delivers a specialized full-stack web application designed to digitalize, manage, and explore eco-tourism routes and travel infrastructure in Bulgaria by combining localized data with artificial intelligence.

---

## 📌 About the Project

This application is a Python-based web project built with the **Flask** framework. It acts as an intelligent assistant that helps users discover, search for, and plan their journeys along various eco-trails. The system uniquely merges a structured local route database with external AI capabilities to generate smart, contextual guidance for hikers.

### Key Features
*   **Smart Trail Discovery:** Search and filter eco-trails dynamically using advanced keyword matching.
*   **Deep Route Insights:** Retrieve detailed route information, difficulty levels, and landmarks.
*   **AI Cognitive Assistant:** Integration with OpenAI API to provide intelligent responses, tips, and custom guidance for travelers.
*   **Geospatial Calculations:** Integrated with OpenRouteService for live route and distance computations.
*   **Responsive Web UI:** A clean, visual interface built using HTML5, modern CSS, and JavaScript.

---

## 🛠️ Tech Stack & Requirements

The project demonstrates strong software engineering fundamentals, utilizing a reliable ecosystem focused on API integrations and clean code separation.

*   **Language:** Python 3.11 or newer
*   **Framework:** Flask
*   **AI Integration:** OpenAI Python SDK
*   **Mapping & Routing:** OpenRouteService API
*   **Environment Management:** python-dotenv

---

## 🚀 Installation & Setup

Follow these steps to clone, configure, and run the project locally on your machine.

### 1. Clone the Repository
Clone or copy the project into your local directory:
```bash
git clone [https://github.com/PlamenMitkov/EcoTrailsProject.git](https://github.com/PlamenMitkov/EcoTrailsProject.git)
cd EcoTrailsProject
2. Set Up a Virtual Environment
Create a Python virtual environment to isolate the project dependencies:

Bash
python -m venv venv
Activate the virtual environment:

Windows:

Bash
venv\Scripts\activate
macOS / Linux:

Bash
source venv/bin/activate
3. Install Dependencies
Install all required packages listed in the requirements.txt file:

Bash
pip install -r requirements.txt
⚙️ Configuration
Create a .env file in the root directory of the project.

Add the following environment variables with your personal API credentials:

Ini, TOML
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTESERVICE_API_KEY=your_openrouteservice_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
OPENAI_API_KEY: Required to power the intelligent response engine.

OPENROUTESERVICE_API_KEY: Required for spatial and routing calculations.

FLASK_SECRET_KEY: Used to secure user sessions locally.

🏃 Running the Application
Once the dependencies are installed and configuration keys are set up, launch the local development server:

Bash
python app.py
Open your web browser and navigate to:
👉 http://127.0.0.1:5000

📂 Project Structure
The codebase is organized cleanly to maintain strict separation of concerns:

Plaintext
├── app.py                  # Main Flask application entry point
├── query.py                # Business logic module for searching and filtering eco-trails
├── requirements.txt        # Managed Python package dependencies
├── data/
│   └── eco.json            # Structured local eco-trails JSON database
├── templates/
│   └── index.html          # Dynamic web interface markup
└── static/
    ├── css/
    │   └── main.css        # Modular application styling
    └── js/
        └── app.js          # Client-side routing and interactive logic
🎓 Academic Core Objectives
As a Bachelor's diploma thesis, this project successfully demonstrates:

Web Engineering: Building lightweight, high-performance web applications using Flask.

API Architecture: Seamlessly orchestrating external API services (OpenAI, OpenRouteService).

Data Management: Implementing efficient querying, filtering, and parsing within a local JSON data warehouse.

AI Integration: Standardizing modern LLM responses to improve end-user UX.

📈 Future Extensions & Roadmap
While V1 serves as a robust foundational core, it is primed for the following architectural expansions:

[ ] Scalability of the local database by expanding data entries inside eco.json.

[ ] Advanced UI optimizations optimized for edge mobile devices (PWA style).

[ ] Granular metadata sorting (e.g., duration, elevation, difficulty scores).

[ ] Secure user registration, profiles, and historical trail bookmarks.

💡 The Evolution: To see how this foundational Python core evolved into an Enterprise-grade Cloud Platform featuring .NET 10, Clean Architecture (CQRS/MediatR), PostgreSQL/PostGIS, React PWA, and a Spatial-RAG Cognitive Assistant, check out the Master's evolution repository.

🤝 Connect & Collaborate
For questions, analytical feedback, or potential collaboration and development ideas, feel free to reach out directly via the author's contact information provided on the main GitHub profile.
