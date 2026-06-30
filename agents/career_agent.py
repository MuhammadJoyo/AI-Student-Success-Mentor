"""
agents/career_agent.py

CareerAgent: the first agent in the AI Student Success Mentor pipeline.

Responsibility (single, well-defined):
    Given a student's profile (degree, skills, interests, etc.),
    suggest 3 career paths that suit them.

How it fits the architecture:
    - This agent never talks to the Gemini SDK directly. It only calls
      GeminiService.generate(), exactly like every other agent.
    - GeminiService is "dumb" about careers — it just talks to Gemini and
      tells us if that failed (via last_call_used_fallback). It is THIS
      agent's job to know what to do when that happens: fall back to a
      simple, rule-based career suggestion using the student's interests
      and skills, so the student always gets a usable answer.
"""

import json
import logging

from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class CareerAgent:
    """
    Suggests 3 suitable career paths for a student.

    Usage:
        agent = CareerAgent()
        result = agent.run(student_profile)

        # result looks like:
        # {
        #     "career_paths": [...],
        #     "source": "gemini"   # or "fallback"
        # }
    """

    # A small, static knowledge base used ONLY when Gemini is unavailable.
    # Keys are lowercase interest keywords; values are 3 career paths that
    # make sense for someone interested in that area. This is intentionally
    # simple — it exists to guarantee the system never returns nothing,
    # not to replace real career guidance.
    INTEREST_TO_CAREERS = {
        "ai": [
            "Machine Learning Engineer",
            "AI Research Assistant",
            "Data Scientist",
        ],
        "data science": [
            "Data Analyst",
            "Data Scientist",
            "Business Intelligence Developer",
        ],
        "web development": [
            "Frontend Developer",
            "Backend Developer",
            "Full-Stack Developer",
        ],
        "cybersecurity": [
            "Security Analyst",
            "Penetration Tester",
            "SOC Analyst",
        ],
        "mobile development": [
            "Android Developer",
            "iOS Developer",
            "Cross-Platform App Developer",
        ],
        "cloud computing": [
            "Cloud Support Engineer",
            "DevOps Engineer",
            "Cloud Solutions Architect",
        ],
    }

    # Used when none of the student's interests match anything in our
    # small knowledge base above. Keeps the fallback path beginner-safe
    # and never empty.
    DEFAULT_CAREERS = [
        "Software Engineer",
        "Junior Web Developer",
        "IT Support Specialist",
    ]

    def __init__(self, gemini_service: GeminiService | None = None) -> None:
        """
        Args:
            gemini_service: Optional pre-built GeminiService instance.
                              Useful for testing (you can pass in a fake/mock).
                              If not provided, a new GeminiService is created,
                              which will read GEMINI_API_KEY from .env itself.
        """
        self.gemini_service = gemini_service or GeminiService()

    def run(self, student_profile: dict) -> dict:
        """
        Main entry point for this agent.

        Args:
            student_profile: dict with at least "skills" and "interests" keys.
                Example:
                {
                    "name": "Muhammad",
                    "degree": "BS Computer Science",
                    "semester": 4,
                    "cgpa": 3.2,
                    "skills": ["Python", "Git"],
                    "interests": ["AI", "Data Science"]
                }

        Returns:
            {
                "career_paths": [str, str, str],
                "source": "gemini" | "fallback"
            }
        """
        # Step 1: ask Gemini first, since AI-generated suggestions are
        # usually more specific and personalized than our static table.
        prompt = self._build_prompt(student_profile)
        raw_response = self.gemini_service.generate(prompt)

        # Step 2: check the flag GeminiService gives us. If Gemini failed
        # for any reason, last_call_used_fallback will be True and
        # raw_response will just be a generic placeholder string —
        # we ignore it completely and build our own answer instead.
        if self.gemini_service.last_call_used_fallback:
            logger.info("Gemini unavailable — using rule-based career suggestions.")
            return self._fallback_response(student_profile)

        # Step 3: Gemini responded, but we still need to safely turn its
        # text into a clean Python list. If parsing fails for any reason
        # (Gemini didn't follow the JSON format we asked for), we treat
        # that the same as a Gemini failure and fall back too — a broken
        # response is no more useful to the student than no response.
        career_paths = self._parse_gemini_response(raw_response)
        if career_paths is None:
            logger.warning("Could not parse Gemini's response — using fallback instead.")
            return self._fallback_response(student_profile)

        return {
            "career_paths": career_paths,
            "source": "gemini",
        }

    def _build_prompt(self, student_profile: dict) -> str:
        """
        Builds the prompt we send to Gemini.

        We explicitly ask for JSON so that _parse_gemini_response() has a
        predictable format to work with. This keeps the prompt simple and
        beginner-friendly while still being reliable.
        """
        skills = ", ".join(student_profile.get("skills", [])) or "no listed skills"
        interests = ", ".join(student_profile.get("interests", [])) or "no listed interests"
        degree = student_profile.get("degree", "an unspecified degree")
        semester = student_profile.get("semester", "an unspecified semester")

        return (
            "You are a career mentor for university students.\n"
            f"Student degree: {degree}\n"
            f"Current semester: {semester}\n"
            f"Skills: {skills}\n"
            f"Interests: {interests}\n\n"
            "Suggest exactly 3 suitable career paths for this student.\n"
            "Respond ONLY with valid JSON in this exact format, "
            "and nothing else (no explanations, no markdown):\n"
            '{"career_paths": ["Career 1", "Career 2", "Career 3"]}'
        )

    def _parse_gemini_response(self, raw_response: str) -> list[str] | None:
        """
        Safely converts Gemini's raw text response into a list of 3
        career path strings.

        Returns None if parsing fails in any way, so the caller knows
        to use the fallback instead of crashing or returning garbage.
        """
        try:
            # Gemini sometimes wraps JSON in markdown code fences even when
            # asked not to — strip those before parsing, just in case.
            cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

            data = json.loads(cleaned)
            career_paths = data.get("career_paths")

            # Basic sanity checks: must be a list of non-empty strings.
            if (
                isinstance(career_paths, list)
                and len(career_paths) > 0
                and all(isinstance(item, str) and item.strip() for item in career_paths)
            ):
                # Always return exactly 3 (truncate if Gemini gave more).
                return [item.strip() for item in career_paths[:3]]

            return None

        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    def _fallback_response(self, student_profile: dict) -> dict:
        """
        Rule-based career suggestion used when Gemini is unavailable
        or returns something we can't parse.

        Logic (kept intentionally simple and transparent):
            1. Look at the student's listed interests.
            2. Match each interest (case-insensitive) against our small
               INTEREST_TO_CAREERS table.
            3. Return the first match found.
            4. If no interest matches anything in our table, return a
               safe set of general default careers instead.
        """
        interests = student_profile.get("interests", [])

        for interest in interests:
            key = interest.strip().lower()
            if key in self.INTEREST_TO_CAREERS:
                return {
                    "career_paths": self.INTEREST_TO_CAREERS[key],
                    "source": "fallback",
                }

        # No interest matched our table — return safe defaults rather
        # than an empty list, so the student always gets something.
        return {
            "career_paths": self.DEFAULT_CAREERS,
            "source": "fallback",
        }