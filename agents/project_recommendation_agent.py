"""
agents/project_recommendation_agent.py

ProjectRecommendationAgent: the fifth and final agent in the AI Student
Success Mentor pipeline.

Responsibility (single, well-defined):
    Given the student's chosen career path(s) and the skills they are
    currently missing (from SkillGapAgent), recommend exactly 3 portfolio
    projects that would help close those gaps while supporting their
    target career.

How it fits the architecture:
    - This agent never talks to the Gemini SDK directly. It only calls
      GeminiService.generate(), exactly like CareerAgent, SkillGapAgent,
      InternshipAgent, and StudyPlannerAgent.
    - GeminiService is "dumb" about projects/careers — it just talks to
      Gemini and tells us if that failed (via last_call_used_fallback).
      It is THIS agent's job to know what to do when that happens: fall
      back to a static, career-keyed project bank, so the student always
      gets 3 usable project ideas even with no internet/API key.
"""

import json
import logging

from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# The output always contains exactly 3 projects, regardless of source.
# Pulled out as a named constant (mirrors TOTAL_WEEKS in
# StudyPlannerAgent) rather than a magic number scattered through the code.
REQUIRED_PROJECT_COUNT = 3


class ProjectRecommendationAgent:
    """
    Recommends exactly 3 portfolio projects suited to a student's chosen
    career path(s) and current skill gaps.

    Usage:
        agent = ProjectRecommendationAgent()
        result = agent.run({
            "career_paths": ["Machine Learning Engineer"],
            "missing_skills": ["TensorFlow", "Deep Learning"]
        })

        # result looks like:
        # {
        #     "recommended_projects": [
        #         {"title": "...", "description": "..."},
        #         {"title": "...", "description": "..."},
        #         {"title": "...", "description": "..."}
        #     ],
        #     "source": "gemini"   # or "fallback"
        # }
    """

    # Static career -> project-bank knowledge base.
    # Used ONLY when Gemini is unavailable or returns something we can't
    # parse/validate. Each career maps to a small bank of project ideas
    # (more than 3, where possible) so the fallback can still pick a
    # reasonable set of 3 rather than always returning the exact same
    # three projects for everyone with that career goal.
    #
    # Keys are lowercase career titles so lookups are case-insensitive.
    CAREER_PROJECT_BANK = {
        "machine learning engineer": [
            {
                "title": "Image Classifier with Transfer Learning",
                "description": (
                    "Build an image classification model using a pretrained "
                    "CNN (e.g. ResNet) and fine-tune it on a custom dataset. "
                    "Demonstrates deep learning and TensorFlow/PyTorch skills."
                ),
            },
            {
                "title": "End-to-End ML Pipeline with Deployment",
                "description": (
                    "Train a model on a real dataset, track experiments, and "
                    "deploy it behind a simple API. Demonstrates the full "
                    "ML lifecycle, not just model training."
                ),
            },
            {
                "title": "Predictive Analytics Dashboard",
                "description": (
                    "Build a dashboard that visualizes predictions from a "
                    "trained model on live or sample data. Demonstrates "
                    "statistics, data handling, and presentation skills."
                ),
            },
            {
                "title": "Recommendation System",
                "description": (
                    "Build a basic recommendation engine (e.g. for movies "
                    "or products) using collaborative filtering. Demonstrates "
                    "applied machine learning and data manipulation with Pandas."
                ),
            },
        ],
        "ai research assistant": [
            {
                "title": "Reproduce a Published ML Paper",
                "description": (
                    "Pick a well-known research paper and reproduce its "
                    "core experiment on a smaller dataset. Demonstrates "
                    "research methods and technical depth."
                ),
            },
            {
                "title": "Literature Review Tool",
                "description": (
                    "Build a tool that summarizes and organizes research "
                    "papers on a chosen topic. Demonstrates research and "
                    "academic writing skills alongside basic NLP."
                ),
            },
            {
                "title": "Statistical Analysis of an Open Dataset",
                "description": (
                    "Perform a rigorous statistical analysis on a public "
                    "dataset and document your methodology. Demonstrates "
                    "statistics and mathematical reasoning."
                ),
            },
        ],
        "data scientist": [
            {
                "title": "End-to-End Data Analysis Project",
                "description": (
                    "Clean, analyze, and visualize a real-world dataset to "
                    "answer a specific business question. Demonstrates "
                    "Pandas, statistics, and data visualization skills."
                ),
            },
            {
                "title": "Predictive Model with SQL-Backed Data",
                "description": (
                    "Pull data from a SQL database, engineer features, and "
                    "train a predictive model. Demonstrates SQL and "
                    "machine learning together."
                ),
            },
            {
                "title": "A/B Testing Simulation",
                "description": (
                    "Simulate an A/B test on sample data and analyze the "
                    "statistical significance of the results. Demonstrates "
                    "statistics and experiment design."
                ),
            },
        ],
        "data analyst": [
            {
                "title": "Sales Performance Dashboard",
                "description": (
                    "Build an interactive dashboard analyzing sales trends "
                    "from a sample dataset using SQL and a visualization "
                    "tool. Demonstrates SQL and data visualization."
                ),
            },
            {
                "title": "Customer Churn Analysis",
                "description": (
                    "Analyze a customer dataset to identify patterns behind "
                    "churn and present findings clearly. Demonstrates "
                    "statistics and Excel/Python analysis skills."
                ),
            },
            {
                "title": "KPI Reporting Automation",
                "description": (
                    "Automate a recurring report (e.g. weekly KPIs) using "
                    "Python or Excel macros. Demonstrates practical "
                    "data-wrangling and reporting skills."
                ),
            },
        ],
        "frontend developer": [
            {
                "title": "Responsive Personal Portfolio Site",
                "description": (
                    "Build a fully responsive personal portfolio using "
                    "HTML, CSS, and JavaScript. Demonstrates responsive "
                    "design and core frontend fundamentals."
                ),
            },
            {
                "title": "Interactive React Dashboard",
                "description": (
                    "Build a dashboard UI in React that fetches and "
                    "displays data from a public API. Demonstrates React "
                    "and JavaScript skills."
                ),
            },
            {
                "title": "Clone a Popular App's UI",
                "description": (
                    "Recreate the interface of a popular app (e.g. a music "
                    "player or chat app) focusing on pixel-accurate, "
                    "responsive layout. Demonstrates CSS and attention to detail."
                ),
            },
        ],
        "backend developer": [
            {
                "title": "REST API with Authentication",
                "description": (
                    "Build a REST API with user authentication and a "
                    "database backend. Demonstrates REST APIs, SQL, and "
                    "Python backend skills."
                ),
            },
            {
                "title": "Task Queue / Job Scheduler Service",
                "description": (
                    "Build a backend service that processes background "
                    "jobs (e.g. sending emails) asynchronously. Demonstrates "
                    "system design and backend architecture."
                ),
            },
            {
                "title": "Versioned API with Git Workflow",
                "description": (
                    "Build a small API and practice proper Git branching, "
                    "commits, and versioning throughout development. "
                    "Demonstrates Git and collaborative dev practices."
                ),
            },
        ],
        "full-stack developer": [
            {
                "title": "Full-Stack To-Do / Task Manager App",
                "description": (
                    "Build a complete task manager with a React frontend, "
                    "a Python backend, and a database. Demonstrates the "
                    "full stack: HTML/CSS/JS, Python, SQL, and REST APIs."
                ),
            },
            {
                "title": "E-Commerce Storefront (Mini)",
                "description": (
                    "Build a small online store with product listings, a "
                    "cart, and a checkout flow. Demonstrates full-stack "
                    "integration and Git-based version control."
                ),
            },
            {
                "title": "Social Media Clone (Core Features)",
                "description": (
                    "Build a simplified social app with posts, likes, and "
                    "a feed. Demonstrates full-stack architecture and "
                    "REST API design end-to-end."
                ),
            },
        ],
        "security analyst": [
            {
                "title": "Home Network Security Audit",
                "description": (
                    "Document and secure a home/lab network, identifying "
                    "vulnerabilities and applying fixes. Demonstrates "
                    "networking and cybersecurity fundamentals."
                ),
            },
            {
                "title": "SIEM Log Analysis Lab",
                "description": (
                    "Set up a free SIEM tool and analyze sample logs to "
                    "detect suspicious activity. Demonstrates SIEM tools "
                    "and incident-response thinking."
                ),
            },
            {
                "title": "Risk Assessment Report for a Sample Organization",
                "description": (
                    "Write a formal risk assessment for a fictional "
                    "company's IT infrastructure. Demonstrates risk "
                    "assessment and security documentation skills."
                ),
            },
        ],
        "penetration tester": [
            {
                "title": "Capture The Flag (CTF) Walkthroughs",
                "description": (
                    "Complete and document solutions to several beginner "
                    "CTF challenges. Demonstrates ethical hacking and "
                    "security tools experience."
                ),
            },
            {
                "title": "Vulnerable Lab Environment Exploitation",
                "description": (
                    "Set up an intentionally vulnerable VM and document "
                    "the full exploitation process. Demonstrates Linux, "
                    "networking, and scripting skills."
                ),
            },
            {
                "title": "Automated Recon Script",
                "description": (
                    "Write a Python script that automates basic "
                    "reconnaissance steps for a penetration test. "
                    "Demonstrates scripting and security tooling."
                ),
            },
        ],
        "android developer": [
            {
                "title": "Personal Expense Tracker App",
                "description": (
                    "Build a native Android app for tracking expenses with "
                    "local storage. Demonstrates Kotlin/Java and the "
                    "Android SDK."
                ),
            },
            {
                "title": "Weather App Using a Public API",
                "description": (
                    "Build an Android app that fetches and displays live "
                    "weather data. Demonstrates REST API integration and "
                    "Android development."
                ),
            },
            {
                "title": "Open-Source Android App Contribution",
                "description": (
                    "Contribute a real feature or bug fix to an open-source "
                    "Android project on GitHub. Demonstrates Git and "
                    "real-world Android codebase experience."
                ),
            },
        ],
        "ios developer": [
            {
                "title": "Habit Tracker App in Swift",
                "description": (
                    "Build a native iOS app for tracking daily habits "
                    "with local persistence. Demonstrates Swift and Xcode skills."
                ),
            },
            {
                "title": "News Reader App Using a Public API",
                "description": (
                    "Build an iOS app that fetches and displays articles "
                    "from a public news API. Demonstrates REST API "
                    "integration in Swift."
                ),
            },
            {
                "title": "Open-Source iOS App Contribution",
                "description": (
                    "Contribute a feature or fix to an open-source iOS "
                    "project on GitHub. Demonstrates Git and real-world "
                    "codebase experience."
                ),
            },
        ],
        "devops engineer": [
            {
                "title": "CI/CD Pipeline for a Sample App",
                "description": (
                    "Set up an automated build-test-deploy pipeline for a "
                    "sample project. Demonstrates CI/CD and Git workflow skills."
                ),
            },
            {
                "title": "Containerized Multi-Service App",
                "description": (
                    "Containerize a multi-service application using "
                    "Docker and orchestrate it locally. Demonstrates "
                    "Docker and system design."
                ),
            },
            {
                "title": "Infrastructure-as-Code Setup",
                "description": (
                    "Provision cloud infrastructure for a sample app using "
                    "an IaC tool. Demonstrates cloud platforms and scripting."
                ),
            },
        ],
        "cloud solutions architect": [
            {
                "title": "Scalable Web App Architecture Diagram + Deployment",
                "description": (
                    "Design and deploy a small web app using a scalable "
                    "cloud architecture (load balancer, auto-scaling). "
                    "Demonstrates AWS/Azure and system design."
                ),
            },
            {
                "title": "Multi-Region Backup and Recovery Plan",
                "description": (
                    "Design and implement a backup/disaster-recovery "
                    "setup across cloud regions. Demonstrates networking "
                    "and security awareness."
                ),
            },
            {
                "title": "Cost-Optimized Cloud Migration Plan",
                "description": (
                    "Write and partially implement a plan to migrate a "
                    "sample on-prem app to the cloud cost-effectively. "
                    "Demonstrates architecture and cloud platform knowledge."
                ),
            },
        ],
        # Generic defaults used when a career isn't found in this table at all.
        "software engineer": [
            {
                "title": "Command-Line Tool for a Real Problem",
                "description": (
                    "Build a CLI tool that solves a genuine everyday "
                    "problem (e.g. file organizer). Demonstrates Python "
                    "fundamentals and clean code structure."
                ),
            },
            {
                "title": "Algorithm Visualizer",
                "description": (
                    "Build a tool that visually demonstrates how common "
                    "algorithms (sorting, searching) work step by step. "
                    "Demonstrates data structures and algorithms knowledge."
                ),
            },
            {
                "title": "Open-Source Contribution",
                "description": (
                    "Find a beginner-friendly open-source project and "
                    "submit a real pull request. Demonstrates Git and "
                    "collaborative software development."
                ),
            },
        ],
    }

    # Used when none of the provided career paths match anything in our
    # bank above. Keeps the fallback path safe and never empty-handed.
    DEFAULT_PROJECTS = [
        {
            "title": "Personal Portfolio Website",
            "description": (
                "Build a simple personal website showcasing your skills "
                "and other projects. Demonstrates foundational web "
                "development skills."
            ),
        },
        {
            "title": "Automation Script for a Daily Task",
            "description": (
                "Write a script that automates a repetitive task in your "
                "daily life or studies. Demonstrates practical "
                "programming and problem-solving."
            ),
        },
        {
            "title": "Open-Source Contribution",
            "description": (
                "Contribute a small fix or feature to any beginner-friendly "
                "open-source project. Demonstrates Git and real-world "
                "collaboration skills."
            ),
        },
    ]

    def __init__(self, gemini_service: GeminiService | None = None) -> None:
        """
        Args:
            gemini_service: Optional pre-built GeminiService instance.
                              Useful for testing with a fake/mock service.
                              If not provided, a new GeminiService is created,
                              which reads GEMINI_API_KEY from .env itself.
        """
        self.gemini_service = gemini_service or GeminiService()

    def run(self, input_data: dict) -> dict:
        """
        Main entry point for this agent.

        Args:
            input_data: dict with:
                "career_paths": list[str]    - career(s) chosen earlier
                                                (usually CareerAgent's output)
                "missing_skills": list[str]  - skills the student still
                                                needs (usually SkillGapAgent's
                                                output)

                Example:
                {
                    "career_paths": ["Machine Learning Engineer"],
                    "missing_skills": ["TensorFlow", "Deep Learning"]
                }

        Returns:
            {
                "recommended_projects": [
                    {"title": str, "description": str}, ...
                ],  # always exactly 3 entries
                "source": "gemini" | "fallback"
            }
        """
        career_paths = input_data.get("career_paths", [])
        missing_skills = input_data.get("missing_skills", [])

        # Without a career path we have nothing meaningful to recommend
        # projects for. Return DEFAULT_PROJECTS rather than an empty list
        # — this is a data problem, not a Gemini problem, so we still
        # label it "fallback" since no AI reasoning took place.
        if not career_paths:
            logger.warning("No career_paths provided — using default project recommendations.")
            return {
                "recommended_projects": self.DEFAULT_PROJECTS,
                "source": "fallback",
            }

        # Step 1: ask Gemini first, since it can tailor project ideas
        # much more specifically (e.g. naming a project that targets the
        # exact missing skill, rather than picking from a fixed bank).
        prompt = self._build_prompt(career_paths, missing_skills)
        raw_response = self.gemini_service.generate(prompt)

        # Step 2: check the flag GeminiService gives us. If Gemini failed
        # for any reason, ignore raw_response entirely (it's just the
        # generic placeholder string) and use our static project bank instead.
        if self.gemini_service.last_call_used_fallback:
            logger.info("Gemini unavailable — using rule-based project recommendations.")
            return self._fallback_response(career_paths)

        # Step 3: Gemini responded — try to parse it into exactly 3
        # validated {title, description} entries. A response we can't
        # parse/validate is just as useless as no response, so we fall
        # back the same way we would on an actual API failure.
        recommended_projects = self._parse_gemini_response(raw_response)
        if recommended_projects is None:
            logger.warning("Could not parse Gemini's response — using fallback instead.")
            return self._fallback_response(career_paths)

        return {
            "recommended_projects": recommended_projects,
            "source": "gemini",
        }

    def _build_prompt(self, career_paths: list, missing_skills: list) -> str:
        """
        Builds the prompt sent to Gemini.

        We explicitly ask for JSON in the exact output shape we need
        (a list of exactly 3 {"title": str, "description": str} objects)
        so _parse_gemini_response() has a predictable format to validate
        against, matching the pattern used in the other agents.
        """
        careers_text = ", ".join(career_paths)
        missing_skills_text = (
            ", ".join(missing_skills) if missing_skills else "no major gaps identified"
        )

        return (
            "You are a career mentor helping a university student build "
            "a portfolio.\n"
            f"Target career path(s): {careers_text}\n"
            f"Skills the student is still missing: {missing_skills_text}\n\n"
            f"Recommend exactly {REQUIRED_PROJECT_COUNT} portfolio projects "
            "that would help this student close their missing skills while "
            "demonstrating ability relevant to their target career. Each "
            "project needs a short, clear title and a 1-2 sentence "
            "description explaining what it involves and what it demonstrates.\n"
            "Respond ONLY with valid JSON in this exact format, "
            "and nothing else (no explanations, no markdown):\n"
            '{"recommended_projects": ['
            '{"title": "...", "description": "..."}, '
            '{"title": "...", "description": "..."}, '
            '{"title": "...", "description": "..."}]}'
        )

    def _parse_gemini_response(self, raw_response: str) -> list[dict] | None:
        """
        Safely converts Gemini's raw text response into exactly
        REQUIRED_PROJECT_COUNT validated {title, description} entries.

        Returns None if parsing fails OR if the structure is wrong in
        any way (wrong project count, missing keys, wrong types) — a
        malformed response is treated exactly like a Gemini failure,
        since the caller can't trust it either way.
        """
        try:
            # Gemini sometimes wraps JSON in markdown code fences even when
            # asked not to — strip those before parsing, just in case.
            cleaned = (
                raw_response.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )

            data = json.loads(cleaned)
            recommended_projects = data.get("recommended_projects")

            if (
                not isinstance(recommended_projects, list)
                or len(recommended_projects) != REQUIRED_PROJECT_COUNT
            ):
                return None

            validated_projects = []
            for entry in recommended_projects:
                if not isinstance(entry, dict):
                    return None

                title = entry.get("title")
                description = entry.get("description")

                # Both title and description must be non-empty strings.
                if (
                    not isinstance(title, str) or not title.strip()
                    or not isinstance(description, str) or not description.strip()
                ):
                    return None

                validated_projects.append({
                    "title": title.strip(),
                    "description": description.strip(),
                })

            return validated_projects

        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    def _fallback_response(self, career_paths: list) -> dict:
        """
        Rule-based project recommendation used when Gemini is unavailable
        or returns something we can't parse/validate.

        Logic (kept simple, transparent, and deterministic):
            1. Use the FIRST career path provided (matches the same
               design decision made in SkillGapAgent and InternshipAgent,
               keeping fallback behavior predictable and consistent
               across the whole pipeline).
            2. Look up that career (case-insensitively) in our static
               CAREER_PROJECT_BANK.
            3. Take the first REQUIRED_PROJECT_COUNT projects from that
               career's bank. Banks are curated with at least 3 entries
               each, so this always succeeds for a matched career.
            4. If no match is found, return DEFAULT_PROJECTS instead of
               an empty list, so the student always gets exactly 3
               project ideas.

        This guarantees the function ALWAYS returns exactly
        REQUIRED_PROJECT_COUNT entries, matched to career where possible.
        """
        primary_career = career_paths[0].strip().lower()

        project_pool = self.CAREER_PROJECT_BANK.get(primary_career, self.DEFAULT_PROJECTS)

        # Always slice to exactly REQUIRED_PROJECT_COUNT, even if a bank
        # entry ever ends up with more or fewer than expected — this is
        # the one place that enforces the "always return 3" guarantee
        # for the fallback path.
        recommended_projects = project_pool[:REQUIRED_PROJECT_COUNT]

        # Safety net: if a career's bank somehow had fewer than 3 entries
        # (shouldn't happen given how CAREER_PROJECT_BANK is curated, but
        # defensive coding matters here), pad with DEFAULT_PROJECTS so we
        # never violate the "always exactly 3" contract.
        if len(recommended_projects) < REQUIRED_PROJECT_COUNT:
            needed = REQUIRED_PROJECT_COUNT - len(recommended_projects)
            recommended_projects = recommended_projects + self.DEFAULT_PROJECTS[:needed]

        return {
            "recommended_projects": recommended_projects,
            "source": "fallback",
        }