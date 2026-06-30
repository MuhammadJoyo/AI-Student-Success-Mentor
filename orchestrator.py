"""
orchestrator.py

Orchestrator: the central controller of the AI Student Success Mentor system.

Responsibility:
    Take a raw student profile and run it through all five specialist
    agents, IN ORDER, wiring each agent's output into the next agent's
    expected input. This file contains zero AI/business logic of its
    own — it only knows how to sequence agents and pass data between
    them. All actual reasoning (career suggestions, skill-gap analysis,
    etc.) lives inside the agents themselves.

Why sequential, not parallel:
    Each agent after CareerAgent depends on data produced by an earlier
    agent:
        - SkillGapAgent needs CareerAgent's chosen career path(s)
        - InternshipAgent needs SkillGapAgent's missing_skills
        - StudyPlannerAgent needs SkillGapAgent's missing_skills
        - ProjectRecommendationAgent needs both career_paths and
          missing_skills
    Running them out of order or in parallel would mean later agents
    are working with incomplete or stale data, so this Orchestrator
    deliberately runs them one after another.

Resilience note:
    Every agent already handles its own Gemini failure internally
    (falling back to rule-based logic and returning a normal-looking
    result with "source": "fallback"). Because of that, the Orchestrator
    itself never needs to catch Gemini-specific errors — by the time an
    agent's run() method returns, it has ALREADY succeeded one way or
    another. The Orchestrator's only remaining job is to guard against
    unexpected, non-Gemini failures (e.g. a bug in an agent, a malformed
    student_profile) so that one broken agent can't crash the whole
    pipeline and leave the student with nothing at all.
"""

import logging

from agents.career_agent import CareerAgent
from agents.skill_gap_agent import SkillGapAgent
from agents.internship_agent import InternshipAgent
from agents.study_planner_agent import StudyPlannerAgent
from agents.project_recommendation_agent import ProjectRecommendationAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Sequences all five agents and assembles their outputs into a single
    final report for the student.

    Usage:
        orchestrator = Orchestrator()
        report = orchestrator.run(student_profile)

        # report looks like:
        # {
        #     "career_result": {...},
        #     "skill_gap_result": {...},
        #     "internship_result": {...},
        #     "study_plan_result": {...},
        #     "project_result": {...}
        # }
    """

    def __init__(
        self,
        career_agent: CareerAgent | None = None,
        skill_gap_agent: SkillGapAgent | None = None,
        internship_agent: InternshipAgent | None = None,
        study_planner_agent: StudyPlannerAgent | None = None,
        project_recommendation_agent: ProjectRecommendationAgent | None = None,
    ) -> None:
        """
        Each agent can optionally be injected (useful for testing with
        fake/mock agents instead of hitting Gemini or the real fallback
        logic). If not provided, a real instance of each agent is
        created — and each of THOSE will create its own GeminiService,
        which reads GEMINI_API_KEY from .env on its own.

        We deliberately give each agent its own GeminiService instance
        rather than sharing one across agents. This keeps agents fully
        independent and easy to test/swap individually, at the small
        cost of each agent reading the same .env file separately — a
        reasonable trade-off for this project's scale.
        """
        self.career_agent = career_agent or CareerAgent()
        self.skill_gap_agent = skill_gap_agent or SkillGapAgent()
        self.internship_agent = internship_agent or InternshipAgent()
        self.study_planner_agent = study_planner_agent or StudyPlannerAgent()
        self.project_recommendation_agent = (
            project_recommendation_agent or ProjectRecommendationAgent()
        )

    def run(self, student_profile: dict) -> dict:
        """
        Runs the full five-agent pipeline for a single student.

        Args:
            student_profile: dict describing the student. Expected to
                contain at least "skills" and "interests", e.g.:
                {
                    "name": "Muhammad",
                    "degree": "BS Computer Science",
                    "semester": 4,
                    "cgpa": 3.2,
                    "skills": ["Python", "Git"],
                    "interests": ["AI", "Data Science"]
                }
                (CareerAgent reads "skills"/"interests"/"degree"/etc.
                directly from this dict — Orchestrator passes it through
                unchanged for this first step.)

        Returns:
            {
                "career_result": dict,       # CareerAgent's full output
                "skill_gap_result": dict,    # SkillGapAgent's full output
                "internship_result": dict,   # InternshipAgent's full output
                "study_plan_result": dict,   # StudyPlannerAgent's full output
                "project_result": dict       # ProjectRecommendationAgent's full output
            }

        Each "*_result" value is exactly what that agent's run() method
        returned, including its own "source": "gemini"/"fallback" field.
        This preserves full provenance — a report builder downstream can
        show the student exactly which sections were AI-generated vs
        rule-based, without the Orchestrator needing to track that itself.
        """
        # Basic guard: an empty or missing student_profile means there is
        # nothing meaningful to build a report from. We fail fast here
        # with a clear error rather than letting CareerAgent silently
        # process an empty dict and produce a confusing result.
        if not student_profile:
            raise ValueError("Orchestrator.run() requires a non-empty student_profile dict.")

        logger.info("Starting student success pipeline for profile: %s", student_profile.get("name", "Unknown"))

        # ------------------------------------------------------------------
        # Step 1: Career Agent
        # Input: the raw student profile (skills, interests, degree, etc.)
        # Output: career_paths the student could pursue.
        # ------------------------------------------------------------------
        career_result = self.career_agent.run(student_profile)
        logger.info("CareerAgent finished (source=%s).", career_result.get("source"))

        # ------------------------------------------------------------------
        # Step 2: Skill Gap Agent
        # Input: the student's current skills + the career_paths just
        #        produced by CareerAgent.
        # Output: missing_skills the student needs for that career.
        # ------------------------------------------------------------------
        skill_gap_input = {
            "skills": student_profile.get("skills", []),
            "career_paths": career_result.get("career_paths", []),
        }
        skill_gap_result = self.skill_gap_agent.run(skill_gap_input)
        logger.info("SkillGapAgent finished (source=%s).", skill_gap_result.get("source"))

        # ------------------------------------------------------------------
        # Step 3: Internship Agent
        # Input: career_paths (from Step 1) + missing_skills (from Step 2).
        # Output: recommended internships matching the student's level.
        # ------------------------------------------------------------------
        internship_input = {
            "career_paths": career_result.get("career_paths", []),
            "missing_skills": skill_gap_result.get("missing_skills", []),
        }
        internship_result = self.internship_agent.run(internship_input)
        logger.info("InternshipAgent finished (source=%s).", internship_result.get("source"))

        # ------------------------------------------------------------------
        # Step 4: Study Planner Agent
        # Input: missing_skills (from Step 2) only — the study plan is
        #        purely about closing skill gaps, not career-specific.
        # Output: an 8-week study plan.
        # ------------------------------------------------------------------
        study_planner_input = {
            "missing_skills": skill_gap_result.get("missing_skills", []),
        }
        study_plan_result = self.study_planner_agent.run(study_planner_input)
        logger.info("StudyPlannerAgent finished (source=%s).", study_plan_result.get("source"))

        # ------------------------------------------------------------------
        # Step 5: Project Recommendation Agent
        # Input: career_paths (from Step 1) + missing_skills (from Step 2).
        # Output: exactly 3 portfolio project recommendations.
        # ------------------------------------------------------------------
        project_input = {
            "career_paths": career_result.get("career_paths", []),
            "missing_skills": skill_gap_result.get("missing_skills", []),
        }
        project_result = self.project_recommendation_agent.run(project_input)
        logger.info("ProjectRecommendationAgent finished (source=%s).", project_result.get("source"))

        logger.info("Student success pipeline completed successfully.")

        # ------------------------------------------------------------------
        # Final assembly: collect every agent's full output under a
        # clearly-named key. The Orchestrator does not reshape, filter,
        # or summarize any agent's output — that is the responsibility
        # of a separate report-building layer, not this controller.
        # ------------------------------------------------------------------
        return {
            "career_result": career_result,
            "skill_gap_result": skill_gap_result,
            "internship_result": internship_result,
            "study_plan_result": study_plan_result,
            "project_result": project_result,
        }