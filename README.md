# 🌿 EcoMuni AI
> **Vibe2Ship Hackathon Submission** | **Track:** Community Hero (Hyperlocal Problem Solver)

EcoMuni AI is a hyper-local civic restoration platform that transforms passive community complaints (like potholes, garbage dumps, or broken streetlights) into a dynamic, AI-triaged, gamified velocity race. 

Instead of grievances sitting in municipal inboxes for months, EcoMuni AI instantly assesses damage, estimates required materials, autonomously drafts official complaints, and rewards neighborhoods that fix their problems the fastest.

## ✨ Key Features

* **🤖 Autonomous AI Triage:** Powered by **Google Gemini 2.5 Flash**. It visually analyzes uploaded civic issues, categorizes them, and assigns a strict Severity Score (1-10).
* **🛡️ Visual Security Gateway:** Utilizes OpenCV for low-light image denoising and a structural mock of Google SynthID to prevent AI-generated image spoofing.
* **📦 Circular Economy BOM:** Automatically generates a structured Bill of Materials (BOM) needed to fix the issue based purely on visual context.
* **🏆 Velocity Gamification Engine:** Ranks local neighborhoods on a real-time leaderboard based on how *fast* they resolve severe issues, using the algorithmic formula: `Points = (Severity * 1000) / Hours to Resolve`.
* **🗺️ Active Civic Mapping:** Real-time Folium/CartoDB map rendering verified and unverified civic hazards across the community.

## 🛠️ Tech Stack

* **Frontend:** Streamlit, Pandas, Folium (Maps)
* **Backend:** FastAPI, Uvicorn, SQLite (SQLAlchemy)
* **AI & Vision:** Google Generative AI SDK (Gemini 2.5 Flash), OpenCV-Python, Pillow

---

## ⚙️ How to Run Locally

If you want to spin up the EcoMuni AI architecture on your local machine, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/EcoMuni-AI.git
cd EcoMuni-AI
```

### 2. Set Up the Environment

Create a virtual environment and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Add Your Google Gemini API Key

Create a `.env` file in the root directory and add a Developer API key from [Google AI Studio](https://aistudio.google.com/):

```text
GEMINI_API_KEY="AIzaSy_YOUR_API_KEY_HERE"
```

### 4. Start the Application

You will need two terminal windows to run the decoupled architecture.

**Terminal 1 (Start the FastAPI Backend):**

```bash
source venv/bin/activate
python -m uvicorn main:app --port 8000
```
*The backend will run on `http://localhost:8000`*

**Terminal 2 (Start the Streamlit Frontend):**

```bash
source venv/bin/activate
python -m streamlit run app.py --server.port 8502
```
*The frontend will open automatically at `http://localhost:8502`*

---

*Built with 💻 and ☕ for the Vibe2Ship 2026 Hackathon.*
