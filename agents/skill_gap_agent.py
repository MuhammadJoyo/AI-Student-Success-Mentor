"""
agents/skill_gap_agent.py

SkillGapAgent: the second agent in the AI Student Success Mentor pipeline.

Responsibility (single, well-defined):
    Given a student's current skills and the career path(s) chosen by
    CareerAgent, identify which skills the student is MISSING for that
    career.

How it fits the architecture:
    - This agent never talks to the Gemini SDK directly. It only calls
      GeminiService.generate(), exactly like CareerAgent does.
    - GeminiService is "dumb" about careers/skills — it just talks to
      Gemini and tells us if that failed (via last_call_used_fallback).
      It is THIS agent's job to know what to do when that happens: fall
      back to a rule-based skill-gap calculation using a static
      career -> required-skills table, so the student always gets a
      usable answer even with no internet/API key.
"""

import json
import logging

from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class SkillGapAgent:
    """
    Identifies the gap between a student's current skills and the
    skills required for their chosen career path(s).

    Usage:
        agent = SkillGapAgent()
        result = agent.run({
            "skills": ["Python", "Git"],
            "career_paths": ["Machine Learning Engineer"]
        })

        # result looks like:
        # {
        #     "missing_skills": [...],
        #     "source": "gemini"   # or "fallback"
        # }
    """

    # Static career -> required-skills knowledge base.
    # Used ONLY when Gemini is unavailable or returns something we can't
    # parse. This is intentionally a simple, hand-maintained table — it
    # exists to guarantee the system always produces a real answer, not
    # to replace Gemini's broader knowledge of the job market.
    #
    # Keys are lowercase career titles so lookups are case-insensitive.
    CAREER_REQUIRED_SKILLS = {
        "machine learning engineer": [
            "Python", "Machine Learning", "Deep Learning", "NumPy",
            "Pandas", "TensorFlow", "PyTorch", "SQL", "Statistics",
        ],
        "ai research assistant": [
            "Python", "Machine Learning", "Research Methods",
            "Statistics", "Mathematics", "Academic Writing",
        ],
        "data scientist": [
            "Python", "SQL", "Statistics", "Machine Learning",
            "Pandas", "Data Visualization", "NumPy",
        ],
        "data analyst": [
            "SQL", "Excel", "Data Visualization", "Statistics", "Python",
        ],
        "business intelligence developer": [
            "SQL", "Power BI", "Data Warehousing", "ETL", "Excel",
        ],
        "frontend developer": [
            "HTML", "CSS", "JavaScript", "React", "Git", "Responsive Design",
        ],
        "backend developer": [
            "Python", "SQL", "REST APIs", "Git", "Databases", "System Design",
        ],
        "full-stack developer": [
            "HTML", "CSS", "JavaScript", "Python", "SQL", "Git", "REST APIs",
        ],
        "security analyst": [
            "Networking", "Linux", "Cybersecurity Fundamentals",
            "SIEM Tools", "Risk Assessment",
        ],
        "penetration tester": [
            "Networking", "Linux", "Python", "Ethical Hacking",
            "Security Tools", "Scripting",
        ],
        "soc analyst": [
            "Networking", "SIEM Tools", "Incident Response", "Linux",
        ],
        "android developer": [
            "Kotlin", "Java", "Android SDK", "Git", "REST APIs",
        ],
        "ios developer": [
            "Swift", "Xcode", "Git", "REST APIs",
        ],
        "cross-platform app developer": [
            "Flutter", "Dart", "React Native", "JavaScript", "Git",
        ],
        "cloud support engineer": [
            "Linux", "Networking", "AWS", "Troubleshooting", "Scripting",
        ],
        "devops engineer": [
            "Linux", "Docker", "CI/CD", "Git", "Cloud Platforms", "Scripting",
        ],
        "cloud solutions architect": [
            "AWS", "Azure", "System Design", "Networking", "Security",
        ],
        # Generic defaults used when a career isn't found in this table at all.
        "software engineer": [
            "Python", "Data Structures", "Algorithms", "Git", "SQL",
        ],
        "junior web developer": [
            "HTML", "CSS", "JavaScript", "Git",
        ],
        "it support specialist": [
            "Networking", "Troubleshooting", "Operating Systems", "Customer Service",
        ],
    }

    # Used when a career path doesn't match anything in our table above.
    # Keeps the fallback path safe and never empty-handed.
    DEFAULT_REQUIRED_SKILLS = ["Python", "Problem Solving", "Communication"]

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
                "skills": list[str]        - student's current skills
                "career_paths": list[str]  - career(s) chosen earlier
                                              (usually CareerAgent's output)

                Example:
                {
                    "skills": ["Python", "Git"],
                    "career_paths": ["Machine Learning Engineer"]
                }

        Returns:
            {
                "missing_skills": [str, ...],
                "source": "gemini" | "fallback"
            }
        """
        current_skills = input_data.get("skills", [])
        career_paths = input_data.get("career_paths", [])

        # If we have no career path to compare against, there is nothing
        # to compute a gap from. Return an empty, clearly-labeled result
        # rather than guessing — this is a data problem, not a Gemini
        # problem, so we still call it "fallback" since no AI reasoning
        # took place.
        if not career_paths:
            logger.warning("No career_paths provided — cannot compute skill gap.")
            return {
                "missing_skills": [],
                "source": "fallback",
            }

        # Step 1: ask Gemini first, since it can reason about skill
        # overlap more flexibly than our static table (e.g. recognizing
        # that "NumPy" and "numpy" are the same skill, or that "OOP in
        # Java" partially covers "OOP" requirements).
        prompt = self._build_prompt(current_skills, career_paths)
        raw_response = self.gemini_service.generate(prompt)

        # Step 2: check the flag GeminiService gives us. If Gemini failed
        # for any reason, ignore raw_response entirely (it's just the
        # generic placeholder string) and compute the gap ourselves.
        if self.gemini_service.last_call_used_fallback:
            logger.info("Gemini unavailable — using rule-based skill gap calculation.")
            return self._fallback_response(current_skills, career_paths)

        # Step 3: Gemini responded — try to parse it into a clean list.
        # A response we can't parse is just as useless as no response,
        # so we fall back the same way we would on an actual API failure.
        missing_skills = self._parse_gemini_response(raw_response)
        if missing_skills is None:
            logger.warning("Could not parse Gemini's response — using fallback instead.")
            return self._fallback_response(current_skills, career_paths)

        return {
            "missing_skills": missing_skills,
            "source": "gemini",
        }

    def _build_prompt(self, current_skills: list, career_paths: list) -> str:
        """
        Builds the prompt sent to Gemini.

        We explicitly ask for JSON so _parse_gemini_response() has a
        predictable format to work with, matching the pattern used in
        CareerAgent for consistency across the whole pipeline.
        """
        skills_text = ", ".join(current_skills) if current_skills else "no listed skills"
        careers_text = ", ".join(career_paths)

        return (
            "You are a career mentor helping a university student identify "
            "skill gaps.\n"
            f"Student's current skills: {skills_text}\n"
            f"Target career path(s): {careers_text}\n\n"
            "Compare the student's current skills against what is typically "
            "required for these career path(s). List the important skills "
            "the student is MISSING (do not repeat skills they already have).\n"
            "Respond ONLY with valid JSON in this exact format, "
            "and nothing else (no explanations, no markdown):\n"
            '{"missing_skills": ["Skill 1", "Skill 2", "Skill 3"]}'
        )

    def _parse_gemini_response(self, raw_response: str) -> list[str] | None:
        """
        Safely converts Gemini's raw text response into a list of
        missing-skill strings.

        Returns None if parsing fails in any way, so the caller knows
        to use the fallback instead of crashing or returning garbage.
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
            missing_skills = data.get("missing_skills")

            # Basic sanity check: must be a list (can be empty — it's
            # valid for a student to already have every required skill).
            if isinstance(missing_skills, list) and all(
                isinstance(item, str) and item.strip() for item in missing_skills
            ):
                return [item.strip() for item in missing_skills]

            return None

        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    def _fallback_response(self, current_skills: list, career_paths: list) -> dict:
        """
        Rule-based skill-gap calculation used when Gemini is unavailable
        or returns something we can't parse.

        Logic (kept simple, transparent, and deterministic):
            1. Normalize the student's current skills to lowercase for
               case-insensitive comparison (e.g. "python" == "Python").
            2. For the FIRST career path provided (matches CareerAgent's
               output order, where the top suggestion is most relevant),
               look up its required skills in our static table.
            3. Compute the set difference: required skills the student
               does NOT already have.
            4. Return that list, preserving the original casing from our
               table (so output looks clean, e.g. "TensorFlow" not "tensorflow").

        If multiple career paths are given, we currently only use the
        first one — this mirrors how a real mentor would focus the gap
        analysis on the student's primary chosen direction rather than
        averaging across unrelated careers.
        """
        # Normalize current skills once for fast, case-insensitive lookup.
        current_skills_lower = {skill.strip().lower() for skill in current_skills}

        # Use the first career path as the primary target for this analysis.
        primary_career = career_paths[0].strip().lower()

        required_skills = self.CAREER_REQUIRED_SKILLS.get(
            primary_career, self.DEFAULT_REQUIRED_SKILLS
        )

        # Set-difference: keep only required skills the student doesn't
        # already have. We compare in lowercase but return the original
        # (nicely-cased) skill name from the table.
        missing_skills = [
            skill for skill in required_skills
            if skill.strip().lower() not in current_skills_lower
        ]

        return {
            "missing_skills": missing_skills,
            "source": "fallback",
        }