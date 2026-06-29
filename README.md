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
├── docs/
│   └── architecture.md
│
├── output/
│
├── app.py
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

### Folder Responsibilities

* **agents/** – Contains the five specialized AI agents responsible for different student-success tasks.
* **services/** – Shared services such as Gemini API integration.
* **docs/** – Architecture and technical documentation.
* **output/** – Generated reports and exported results.
* **app.py** – Main application entry point.
* **README.md** – Project overview, setup instructions, and documentation.
* **requirements.txt** – Python dependencies.
