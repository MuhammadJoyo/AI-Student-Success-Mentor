# AI Student Success Mentor

An intelligent multi-agent career guidance platform that helps university students discover career paths, identify skill gaps, find relevant internships, build structured study plans, and receive portfolio project recommendations.

---

## Overview

AI Student Success Mentor is a multi-agent AI system built using Python, Flask, and the Gemini API.

The platform analyzes a student's profile and generates a personalized roadmap through five specialized agents working together in a sequential pipeline.

The system remains functional even when Gemini API is unavailable by automatically switching to rule-based fallback recommendations.

---

## Features

### Career Recommendation Agent
Suggests suitable career paths based on:

- Degree Program
- Skills
- Interests
- Academic Background

### Skill Gap Analysis Agent
Identifies missing skills required for the recommended career path.

### Internship Recommendation Agent
Suggests realistic internship opportunities that align with career goals and current skill level.

### Study Planner Agent
Generates a personalized 8-week learning roadmap.

### Project Recommendation Agent
Suggests portfolio-worthy projects to strengthen practical experience.

### Fallback System
If Gemini API is unavailable or quota is exceeded, the platform automatically switches to a rule-based fallback engine.

### Modern Frontend Dashboard
- Responsive Design
- Glassmorphism UI
- Real-Time Analysis Workflow
- Interactive Dashboard
- Multi-Agent Visualization

---

## System Architecture

The system follows a sequential multi-agent pipeline.

```text
Student Profile
       │
       ▼
 Career Agent
       │
       ▼
 Skill Gap Agent
       │
       ▼
 ┌──────────────┬──────────────┬──────────────┐
 ▼              ▼              ▼
Internship   Study Planner   Project Agent
     │
     ▼
Report Generator
     │
     ▼
 Flask API
     │
     ▼
Frontend Dashboard
```

---

## Tech Stack

### Backend

- Python
- Flask
- Flask-CORS
- Google Gemini API
- Python Dotenv

### Frontend

- HTML5
- CSS3
- JavaScript
- Glassmorphism UI Design

### Version Control

- Git
- GitHub

---

## Project Structure

```text
AI-Student-Success-Mentor/
│
├── agents/
│   ├── career_agent.py
│   ├── skill_gap_agent.py
│   ├── internship_agent.py
│   ├── study_planner_agent.py
│   └── project_recommendation_agent.py
│
├── services/
│   └── gemini_service.py
│
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── docs/
│   └── architecture.md
│
├── output/
│
├── screenshots/
│
├── api.py
├── app.py
├── orchestrator.py
├── report_generator.py
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/MuhammadJoyo/AI-Student-Success-Mentor.git
cd AI-Student-Success-Mentor
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Activate Virtual Environment

Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## Running The Project

### Run Flask Server

```bash
py api.py
```

or

```bash
python api.py
```

Open:

```text
http://127.0.0.1:5000
```

---

## Screenshots

### Homepage

![Homepage](screenshots/01-homepage.png)

### Specialized Agents

![Agents](screenshots/02-agents-section.png)

### Architecture

![Architecture](screenshots/03-architecture.png)

### Student Profile Form

![Profile Form](screenshots/04-profile-form.png)

### Analysis Pipeline

![Loading Screen](screenshots/05-loading-screen.png)

### Results Dashboard

![Dashboard](screenshots/06-results-top.png)

### Study Plan and Projects

![Dashboard Bottom](screenshots/07-results-bottom.png)

---

## Example Output

The platform generates:

- Career Recommendations
- Skill Gap Analysis
- Internship Suggestions
- 8 Week Study Plan
- Portfolio Project Recommendations

All results are displayed in a modern dashboard interface.

---

## Future Improvements

- User Authentication
- Database Integration
- PDF Report Export
- Real Internship APIs
- Resume Analyzer
- AI Interview Coach
- Job Recommendation Engine
- Cloud Deployment

---

## Author

Muhammad Joyo

BS Computer Science Student

Sukkur IBA University

---

## License

This project is developed for educational and learning purposes.