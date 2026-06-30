"""
agents/internship_agent.py

InternshipAgent: the third agent in the AI Student Success Mentor pipeline.

Responsibility (single, well-defined):
    Given the student's chosen career path(s) and the skills they are
    currently missing (from SkillGapAgent), recommend internship roles
    that fit where the student currently stands.

How it fits the architecture:
    - This agent never talks to the Gemini SDK directly. It only calls
      GeminiService.generate(), exactly like CareerAgent and SkillGapAgent.
    - GeminiService is "dumb" about careers/internships — it just talks to
      Gemini and tells us if that failed (via last_call_used_fallback).
      It is THIS agent's job to know what to do when that happens: fall
      back to a static, career-keyed internship recommendation table, so
      the student always gets a usable answer even with no internet/API key.
"""

import json
import logging

from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class InternshipAgent:
    """
    Recommends internship roles suited to a student's chosen career
    path(s) and current skill level.

    Usage:
        agent = InternshipAgent()
        result = agent.run({
            "career_paths": ["Machine Learning Engineer"],
            "missing_skills": ["TensorFlow", "Deep Learning"]
        })

        # result looks like:
        # {
        #     "recommended_internships": [...],
        #     "source": "gemini"   # or "fallback"
        # }
    """

    # Static career -> internship-roles knowledge base.
    # Used ONLY when Gemini is unavailable or returns something we can't
    # parse. Each entry lists realistic, entry-level internship titles a
    # student could reasonably apply for while still closing skill gaps —
    # this is a simple, hand-maintained table meant to guarantee the
    # system always returns something useful, not to replace a live
    # internship listings dataset.
    #
    # Keys are lowercase career titles so lookups are case-insensitive.
    CAREER_TO_INTERNSHIPS = {
        "machine learning engineer": [
            "Machine Learning Intern",
            "AI/ML Research Intern",
            "Data Science Intern",
        ],
        "ai research assistant": [
            "AI Research Intern",
            "Machine Learning Research Assistant (Internship)",
            "University Research Lab Intern",
        ],
        "data scientist": [
            "Data Science Intern",
            "Data Analytics Intern",
            "Business Intelligence Intern",
        ],
        "data analyst": [
            "Data Analyst Intern",
            "Reporting & Analytics Intern",
            "Business Analyst Intern",
        ],
        "business intelligence developer": [
            "BI Developer Intern",
            "Data Warehousing Intern",
            "Reporting Intern",
        ],
        "frontend developer": [
            "Frontend Developer Intern",
            "UI Engineering Intern",
            "Web Development Intern",
        ],
        "backend developer": [
            "Backend Developer Intern",
            "API Development Intern",
            "Software Engineering Intern",
        ],
        "full-stack developer": [
            "Full-Stack Developer Intern",
            "Software Engineering Intern",
            "Web Development Intern",
        ],
        "security analyst": [
            "Cybersecurity Intern",
            "SOC Intern",
            "IT Security Intern",
        ],
        "penetration tester": [
            "Ethical Hacking Intern",
            "Security Testing Intern",
            "Cybersecurity Intern",
        ],
        "soc analyst": [
            "SOC Analyst Intern",
            "Security Operations Intern",
            "IT Security Intern",
        ],
        "android developer": [
            "Android Developer Intern",
            "Mobile App Development Intern",
        ],
        "ios developer": [
            "iOS Developer Intern",
            "Mobile App Development Intern",
        ],
        "cross-platform app developer": [
            "Mobile App Development Intern",
            "Flutter/React Native Intern",
        ],
        "cloud support engineer": [
            "Cloud Support Intern",
            "IT Infrastructure Intern",
        ],
        "devops engineer": [
            "DevOps Intern",
            "Site Reliability Engineering Intern",
            "Cloud Infrastructure Intern",
        ],
        "cloud solutions architect": [
            "Cloud Engineering Intern",
            "Solutions Architecture Intern",
        ],
        # Generic defaults used when a career isn't found in this table at all.
        "software engineer": [
            "Software Engineering Intern",
            "Junior Developer Intern",
        ],
        "junior web developer": [
            "Web Development Intern",
            "Frontend Developer Intern",
        ],
        "it support specialist": [
            "IT Support Intern",
            "Technical Support Intern",
        ],
    }

    # Used when none of the provided career paths match anything in our
    # table above. Keeps the fallback path safe and never empty-handed.
    DEFAULT_INTERNSHIPS = [
        "General Internship Program",
        "Software Engineering Intern",
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
                "recommended_internships": [str, ...],
                "source": "gemini" | "fallback"
            }
        """
        career_paths = input_data.get("career_paths", [])
        missing_skills = input_data.get("missing_skills", [])

        # Without a career path we have nothing to recommend internships
        # for. Return an empty, clearly-labeled result rather than
        # guessing — this is a data problem, not a Gemini problem, so we
        # still label it "fallback" since no AI reasoning took place.
        if not career_paths:
            logger.warning("No career_paths provided — cannot recommend internships.")
            return {
                "recommended_internships": [],
                "source": "fallback",
            }

        # Step 1: ask Gemini first, since it can tailor internship
        # suggestions more precisely (e.g. factoring in which specific
        # skills are missing, current market conditions, or company-level
        # detail our static table doesn't have).
        prompt = self._build_prompt(career_paths, missing_skills)
        raw_response = self.gemini_service.generate(prompt)

        # Step 2: check the flag GeminiService gives us. If Gemini failed
        # for any reason, ignore raw_response entirely (it's just the
        # generic placeholder string) and use our static table instead.
        if self.gemini_service.last_call_used_fallback:
            logger.info("Gemini unavailable — using rule-based internship recommendations.")
            return self._fallback_response(career_paths)

        # Step 3: Gemini responded — try to parse it into a clean list.
        # A response we can't parse is just as useless as no response,
        # so we fall back the same way we would on an actual API failure.
        recommended_internships = self._parse_gemini_response(raw_response)
        if recommended_internships is None:
            logger.warning("Could not parse Gemini's response — using fallback instead.")
            return self._fallback_response(career_paths)

        return {
            "recommended_internships": recommended_internships,
            "source": "gemini",
        }

    def _build_prompt(self, career_paths: list, missing_skills: list) -> str:
        """
        Builds the prompt sent to Gemini.

        We explicitly ask for JSON so _parse_gemini_response() has a
        predictable format to work with, matching the pattern used in
        CareerAgent and SkillGapAgent for consistency across the pipeline.
        """
        careers_text = ", ".join(career_paths)
        missing_skills_text = (
            ", ".join(missing_skills) if missing_skills else "no major gaps identified"
        )

        return (
            "You are a career mentor helping a university student find "
            "suitable internships.\n"
            f"Target career path(s): {careers_text}\n"
            f"Skills the student is still missing: {missing_skills_text}\n\n"
            "Recommend 3 realistic, entry-level internship roles this "
            "student could apply for right now, given their current "
            "career goal and skill level. Prefer roles that would help "
            "them close their missing skills while gaining experience.\n"
            "Respond ONLY with valid JSON in this exact format, "
            "and nothing else (no explanations, no markdown):\n"
            '{"recommended_internships": ["Internship 1", "Internship 2", "Internship 3"]}'
        )

    def _parse_gemini_response(self, raw_response: str) -> list[str] | None:
        """
        Safely converts Gemini's raw text response into a list of
        internship recommendation strings.

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
            recommended_internships = data.get("recommended_internships")

            # Basic sanity check: must be a non-empty list of non-empty strings.
            if (
                isinstance(recommended_internships, list)
                and len(recommended_internships) > 0
                and all(
                    isinstance(item, str) and item.strip()
                    for item in recommended_internships
                )
            ):
                return [item.strip() for item in recommended_internships]

            return None

        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    def _fallback_response(self, career_paths: list) -> dict:
        """
        Rule-based internship recommendation used when Gemini is
        unavailable or returns something we can't parse.

        Logic (kept simple, transparent, and deterministic):
            1. Use the FIRST career path provided (matches CareerAgent's
               output order, where the top suggestion is most relevant)
               as the primary target for this recommendation.
            2. Look up that career (case-insensitively) in our static
               CAREER_TO_INTERNSHIPS table.
            3. If no match is found, return DEFAULT_INTERNSHIPS instead
               of an empty list, so the student always gets something.

        If multiple career paths are given, we currently only use the
        first one — this mirrors the same design decision made in
        SkillGapAgent, keeping the fallback's behavior predictable and
        consistent across the pipeline.
        """
        primary_career = career_paths[0].strip().lower()

        recommended_internships = self.CAREER_TO_INTERNSHIPS.get(
            primary_career, self.DEFAULT_INTERNSHIPS
        )

        return {
            "recommended_internships": recommended_internships,
            "source": "fallback",
        }