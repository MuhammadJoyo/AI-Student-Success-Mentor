"""
agents/study_planner_agent.py

StudyPlannerAgent: the fourth agent in the AI Student Success Mentor pipeline.

Responsibility (single, well-defined):
    Given the skills a student is missing (from SkillGapAgent), build a
    structured 8-week study plan that helps them close those gaps in a
    sensible order.

How it fits the architecture:
    - This agent never talks to the Gemini SDK directly. It only calls
      GeminiService.generate(), exactly like CareerAgent, SkillGapAgent,
      and InternshipAgent.
    - GeminiService is "dumb" about study planning — it just talks to
      Gemini and tells us if that failed (via last_call_used_fallback).
      It is THIS agent's job to know what to do when that happens: fall
      back to a deterministic week-by-week distribution of the missing
      skills, so the student always gets a complete 8-week plan even
      with no internet/API key.
"""

import json
import logging

from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# The plan always has exactly 8 weeks, regardless of how many skills
# are missing or where the data comes from (Gemini or fallback). This
# is a hard requirement, not a default, so it's pulled out as a named
# constant rather than a magic number scattered through the code.
TOTAL_WEEKS = 8


class StudyPlannerAgent:
    """
    Builds an 8-week study plan to help a student close their skill gaps.

    Usage:
        agent = StudyPlannerAgent()
        result = agent.run({
            "missing_skills": ["TensorFlow", "Deep Learning", "SQL"]
        })

        # result looks like:
        # {
        #     "study_plan": [
        #         {"week": 1, "focus": "..."},
        #         ...
        #         {"week": 8, "focus": "..."}
        #     ],
        #     "source": "gemini"   # or "fallback"
        # }
    """

    # Labels used to fill out any weeks left over after every missing
    # skill has already been assigned its own week. This keeps the plan
    # useful (revision + practical application) instead of just leaving
    # weeks blank or repeating "no topic" placeholders.
    FILLER_WEEK_LABELS = [
        "Revision and practice of previously covered skills",
        "Build a small project applying the skills learned so far",
        "Mock interview practice and portfolio polishing",
        "Revise weak areas and consolidate learning",
    ]

    # Used only if missing_skills is completely empty — keeps the plan
    # useful instead of returning 8 identical "nothing to do" weeks.
    NO_GAPS_LABEL = "General skill-building and portfolio project work"

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
                "missing_skills": list[str]  - skills the student still
                                                needs (usually SkillGapAgent's
                                                output)

                Example:
                {
                    "missing_skills": ["TensorFlow", "Deep Learning", "SQL"]
                }

        Returns:
            {
                "study_plan": [{"week": int, "focus": str}, ...],  # always 8 entries
                "source": "gemini" | "fallback"
            }
        """
        missing_skills = input_data.get("missing_skills", [])

        # Step 1: ask Gemini first, since it can sequence topics more
        # intelligently than a flat round-robin (e.g. putting foundational
        # skills like "Statistics" before "Deep Learning" that builds on it).
        prompt = self._build_prompt(missing_skills)
        raw_response = self.gemini_service.generate(prompt)

        # Step 2: check the flag GeminiService gives us. If Gemini failed
        # for any reason, ignore raw_response entirely (it's just the
        # generic placeholder string) and build the plan ourselves.
        if self.gemini_service.last_call_used_fallback:
            logger.info("Gemini unavailable — using rule-based 8-week study plan.")
            return self._fallback_response(missing_skills)

        # Step 3: Gemini responded — try to parse it into a clean,
        # correctly-shaped 8-week plan. A response we can't parse or
        # that doesn't have exactly 8 weeks is just as useless as no
        # response, so we fall back the same way we would on an actual
        # API failure.
        study_plan = self._parse_gemini_response(raw_response)
        if study_plan is None:
            logger.warning("Could not parse Gemini's response — using fallback instead.")
            return self._fallback_response(missing_skills)

        return {
            "study_plan": study_plan,
            "source": "gemini",
        }

    def _build_prompt(self, missing_skills: list) -> str:
        """
        Builds the prompt sent to Gemini.

        We explicitly ask for JSON in the exact output shape we need
        (a list of {"week": int, "focus": str} objects, exactly 8 of
        them) so _parse_gemini_response() has a predictable format to
        validate against, matching the pattern used in the other agents.
        """
        skills_text = (
            ", ".join(missing_skills)
            if missing_skills
            else "no specific gaps identified — focus on general skill-building"
        )

        return (
            "You are a career mentor building a study plan for a "
            "university student.\n"
            f"Skills the student needs to learn: {skills_text}\n\n"
            f"Create a study plan covering exactly {TOTAL_WEEKS} weeks. "
            "Distribute the skills across the weeks in a sensible learning "
            "order (foundational topics before advanced ones). If there are "
            "fewer skills than weeks, use the remaining weeks for revision, "
            "a small project, or interview/portfolio preparation.\n"
            "Respond ONLY with valid JSON in this exact format, "
            "and nothing else (no explanations, no markdown):\n"
            '{"study_plan": ['
            '{"week": 1, "focus": "..."}, '
            '{"week": 2, "focus": "..."}, '
            "... continue through "
            f'{{"week": {TOTAL_WEEKS}, "focus": "..."}}]}}'
        )

    def _parse_gemini_response(self, raw_response: str) -> list[dict] | None:
        """
        Safely converts Gemini's raw text response into a validated
        8-week study plan.

        Returns None if parsing fails OR if the structure is wrong in
        any way (wrong number of weeks, missing keys, wrong types) — a
        malformed plan is treated exactly like a Gemini failure, since
        the caller can't trust it either way.
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
            study_plan = data.get("study_plan")

            if not isinstance(study_plan, list) or len(study_plan) != TOTAL_WEEKS:
                return None

            validated_plan = []
            for entry in study_plan:
                if not isinstance(entry, dict):
                    return None

                week = entry.get("week")
                focus = entry.get("focus")

                # Week must be an int and focus must be a non-empty string.
                # We don't strictly enforce week == index+1 here (Gemini
                # might order them differently), but every week must be
                # present and every focus must be real text.
                if not isinstance(week, int) or not isinstance(focus, str) or not focus.strip():
                    return None

                validated_plan.append({"week": week, "focus": focus.strip()})

            return validated_plan

        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    def _fallback_response(self, missing_skills: list) -> dict:
        """
        Rule-based 8-week study plan used when Gemini is unavailable or
        returns something we can't parse/validate.

        Logic (kept simple, transparent, and deterministic):
            1. Take the missing skills in the order they were provided
               (assumed to already be roughly prioritized by SkillGapAgent).
            2. Assign one skill per week, starting from week 1.
            3. If there are MORE missing skills than weeks (more than 8),
               only the first 8 are scheduled — the plan still always has
               exactly 8 weeks, never more.
            4. If there are FEWER missing skills than weeks, the remaining
               weeks are filled with revision/project/interview-prep
               labels from FILLER_WEEK_LABELS, cycling through them if
               needed so every week still has a meaningful focus.
            5. If there are NO missing skills at all, every week falls
               back to a general skill-building label so the plan is
               still useful rather than empty.

        This guarantees the function ALWAYS returns exactly TOTAL_WEEKS
        entries, regardless of how many (or how few) skills were passed in.
        """
        study_plan = []

        # Clean up the skill list once: drop empty/whitespace-only entries.
        cleaned_skills = [skill.strip() for skill in missing_skills if skill and skill.strip()]

        for week_number in range(1, TOTAL_WEEKS + 1):
            skill_index = week_number - 1

            if skill_index < len(cleaned_skills):
                # This week still has a real skill gap to assign.
                focus = f"Learn and practice: {cleaned_skills[skill_index]}"
            elif cleaned_skills:
                # We've run out of skills — use a filler label, cycling
                # through the list if we need more filler weeks than we
                # have unique labels for.
                filler_index = (skill_index - len(cleaned_skills)) % len(self.FILLER_WEEK_LABELS)
                focus = self.FILLER_WEEK_LABELS[filler_index]
            else:
                # No missing skills were provided at all.
                focus = self.NO_GAPS_LABEL

            study_plan.append({"week": week_number, "focus": focus})

        return {
            "study_plan": study_plan,
            "source": "fallback",
        }