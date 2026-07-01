# AI Student Success Mentor

An intelligent multi-agent career guidance platform that helps university students discover career paths, identify skill gaps, find relevant internships, build structured study plans, and receive portfolio project recommendations.

---

## Overview

AI Student Success Mentor is a multi-agent AI system built using Python, Flask, and Google Gemini.

The platform analyzes a student's academic profile and generates a personalized success roadmap through five specialized AI agents working together in a sequential pipeline.

The system remains functional even when Gemini API is unavailable by automatically switching to a rule-based fallback engine.

---

## Problem Statement

Many university students struggle with:

- Choosing the right career path
- Understanding industry skill requirements
- Finding suitable internships
- Building structured learning plans
- Creating portfolio-worthy projects

AI Student Success Mentor solves these challenges by providing personalized recommendations through a coordinated multi-agent architecture.

---

## Features

### Career Recommendation Agent

Suggests suitable career paths based on:

- Degree Program
- Current Skills
- Academic Background
- Interests

### Skill Gap Analysis Agent

Identifies missing skills required for the recommended career path.

### Internship Recommendation Agent

Suggests realistic internship opportunities aligned with the student's profile.

### Study Planner Agent

Generates a personalized 8-week learning roadmap.

### Portfolio Project Agent

Recommends portfolio-worthy projects to strengthen practical experience.

### Gemini AI Integration

Uses Google Gemini for intelligent reasoning and personalized recommendations.

### Rule-Based Fallback Engine

Automatically switches to fallback recommendations if Gemini is unavailable or quota is exceeded.

### Modern Dashboard

- Responsive Design
- Glassmorphism UI
- Real-Time Analysis Workflow
- Interactive Results Dashboard
- Multi-Agent Visualization

---

## Multi-Agent Architecture

The platform follows a sequential orchestration workflow.

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
- Responsive UI Design

### Development Tools

- Git
- GitHub
- Vercel

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
│   └── project_agent.py
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
├── screenshots/
│
├── output/
│
├── api.py
├── app.py
├── orchestrator.py
├── report_generator.py
├── vercel.json
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

### Activate Environment

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

## Running Locally

```bash
python api.py
```

Open:

```text
http://127.0.0.1:5000
```

---

## Deployment

This project supports deployment on:

- Vercel
- Render
- Railway

### Deploy on Vercel

1. Push project to GitHub
2. Import repository into Vercel
3. Add Environment Variables

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

4. Deploy

A `vercel.json` configuration file is included for deployment.

---

## Screenshots

### Homepage

![Homepage](screenshots/01-homepage-hero.png)

### Specialized Agents

![Agents](screenshots/02-specialized-agents.png)

### Architecture

![Architecture](screenshots/03-system-architecture.png)

### Student Profile Form

![Profile Form](screenshots/04-student-profile-form.png)

### Analysis Pipeline

![Analysis Pipeline](screenshots/05-analysis-pipeline.png)

### Personalized Dashboard

![Dashboard](screenshots/06-personalized-roadmap-dashboard.png)

### 8 Week Learning Roadmap

![Study Plan](screenshots/07-eight-week-learning-roadmap.png)

### Portfolio Project Recommendations

![Projects](screenshots/08-portfolio-project-recommendations.png)

---

## Example Output

The platform generates:

- Career Recommendations
- Skill Gap Analysis
- Internship Recommendations
- Personalized Learning Roadmap
- Portfolio Project Suggestions

All results are displayed through an interactive dashboard.

---

## Kaggle AI Agents Capstone Project

This project was developed for:

**AI Agents: Intensive Vibe Coding Capstone Project (Kaggle x Google)**

The solution demonstrates:

- Multi-Agent Systems
- Agent Orchestration
- Gemini AI Integration
- Rule-Based Fallback Design
- Deployable Architecture
- Modern User Experience

Track: **Agents for Good**

---

## Future Improvements

- User Authentication
- Database Integration
- PDF Report Export
- Resume Analyzer
- AI Interview Coach
- Real Internship APIs
- Job Recommendation Engine
- Cloud Analytics

---

## Author

**Muhammad Joyo**

BS Computer Science

Sukkur IBA University

---

## License

This project is developed for educational and learning purposes.