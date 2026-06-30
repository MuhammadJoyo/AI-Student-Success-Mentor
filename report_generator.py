"""
report_generator.py

ReportGenerator: turns the Orchestrator's raw results dictionary into a
clean, professional Markdown report that a student can actually read.

Responsibility:
    This file knows NOTHING about careers, skills, Gemini, or fallback
    logic. It only knows how to take the structured dictionary produced
    by Orchestrator.run() and format it as readable Markdown. This keeps
    formatting completely separate from the agents/orchestrator — if we
    ever want to change the report's look (or add an HTML/PDF version
    later), we only touch this file.

Where this fits in the pipeline:
    student_profile -> Orchestrator.run() -> results dict -> ReportGenerator.generate() -> Markdown string
"""


class ReportGenerator:
    """
    Builds a Markdown report from the Orchestrator's results dictionary.

    Usage:
        orchestrator = Orchestrator()
        results = orchestrator.run(student_profile)

        report_generator = ReportGenerator()
        markdown_report = report_generator.generate(results)

        print(markdown_report)
        # or save it to a file, show it in a notebook, etc.
    """

    def generate(self, results: dict) -> str:
        """
        Main entry point for this class.

        Args:
            results: the dictionary returned by Orchestrator.run(), e.g.:
                {
                    "career_result": {"career_paths": [...], "source": "gemini"},
                    "skill_gap_result": {"missing_skills": [...], "source": "fallback"},
                    "internship_result": {"recommended_internships": [...], "source": "gemini"},
                    "study_plan_result": {"study_plan": [{"week": 1, "focus": "..."}], "source": "fallback"},
                    "project_result": {"recommended_projects": [{"title": "...", "description": "..."}], "source": "gemini"}
                }

        Returns:
            A single Markdown-formatted string containing the full report.
        """
        # We build the report section by section, then join everything
        # together at the end. Each "_build_..." method below is small,
        # focused, and easy to read on its own — this is what makes the
        # code beginner-friendly even though the final report has many parts.
        sections = [
            self._build_title(),
            self._build_career_section(results),
            self._build_skill_gap_section(results),
            self._build_internship_section(results),
            self._build_study_plan_section(results),
            self._build_project_section(results),
            self._build_sources_section(results),
        ]

        # Join all sections with a blank line between them so the
        # Markdown renders with clean spacing between headings.
        return "\n\n".join(sections)

    # ----------------------------------------------------------------------
    # Section builders
    # Each method below builds ONE section of the report and returns it
    # as a plain Markdown string. Keeping them separate makes it easy to
    # find and edit a single section without touching the others.
    # ----------------------------------------------------------------------

    def _build_title(self) -> str:
        """Builds the main report title (the very first line of the report)."""
        return "# AI Student Success Mentor Report"

    def _build_career_section(self, results: dict) -> str:
        """
        Builds the 'Career Recommendations' section.

        Reads career_paths from career_result. If it's missing or empty
        for any reason, we still show the heading with a friendly
        message instead of leaving a blank/broken section — this keeps
        the report looking complete even if upstream data was incomplete.
        """
        career_result = results.get("career_result", {})
        career_paths = career_result.get("career_paths", [])

        lines = ["## Career Recommendations"]

        if career_paths:
            # Show each career path as its own bullet point, numbered
            # so the student can clearly see this is a ranked list of
            # suggestions, not just a random set of options.
            for index, career in enumerate(career_paths, start=1):
                lines.append(f"{index}. {career}")
        else:
            lines.append("No career recommendations were generated.")

        return "\n".join(lines)

    def _build_skill_gap_section(self, results: dict) -> str:
        """
        Builds the 'Skill Gap Analysis' section.

        Reads missing_skills from skill_gap_result. An empty list here
        is actually a GOOD outcome (it can mean the student already has
        every required skill), so we phrase that case positively instead
        of treating it like an error.
        """
        skill_gap_result = results.get("skill_gap_result", {})
        missing_skills = skill_gap_result.get("missing_skills", [])

        lines = ["## Skill Gap Analysis"]

        if missing_skills:
            lines.append("Based on your target career, here are the skills you should focus on:")
            for skill in missing_skills:
                lines.append(f"- {skill}")
        else:
            lines.append("Great news! No major skill gaps were identified for your target career.")

        return "\n".join(lines)

    def _build_internship_section(self, results: dict) -> str:
        """
        Builds the 'Internship Recommendations' section.

        Reads recommended_internships from internship_result.
        """
        internship_result = results.get("internship_result", {})
        recommended_internships = internship_result.get("recommended_internships", [])

        lines = ["## Internship Recommendations"]

        if recommended_internships:
            for internship in recommended_internships:
                lines.append(f"- {internship}")
        else:
            lines.append("No internship recommendations were generated.")

        return "\n".join(lines)

    def _build_study_plan_section(self, results: dict) -> str:
        """
        Builds the '8 Week Study Plan' section.

        Reads study_plan from study_plan_result. Each entry is expected
        to look like {"week": 1, "focus": "..."} (this is exactly the
        shape StudyPlannerAgent guarantees, even in fallback mode), so we
        format each one as "Week N: focus" for easy reading.
        """
        study_plan_result = results.get("study_plan_result", {})
        study_plan = study_plan_result.get("study_plan", [])

        lines = ["## 8 Week Study Plan"]

        if study_plan:
            for week_entry in study_plan:
                # Use .get() with safe defaults here too, in case a week
                # entry is ever missing a key for some unexpected reason —
                # this way the report still shows something instead of
                # crashing while looping through the plan.
                week_number = week_entry.get("week", "?")
                focus = week_entry.get("focus", "No focus specified")
                lines.append(f"- **Week {week_number}:** {focus}")
        else:
            lines.append("No study plan was generated.")

        return "\n".join(lines)

    def _build_project_section(self, results: dict) -> str:
        """
        Builds the 'Portfolio Projects' section.

        Reads recommended_projects from project_result. Each entry is
        expected to look like {"title": "...", "description": "..."}
        (this is exactly the shape ProjectRecommendationAgent guarantees,
        even in fallback mode).
        """
        project_result = results.get("project_result", {})
        recommended_projects = project_result.get("recommended_projects", [])

        lines = ["## Portfolio Projects"]

        if recommended_projects:
            for project in recommended_projects:
                title = project.get("title", "Untitled Project")
                description = project.get("description", "No description provided.")
                # Bold the title, then describe it on the same bullet so
                # each project reads as one clean, self-contained item.
                lines.append(f"- **{title}** — {description}")
        else:
            lines.append("No project recommendations were generated.")

        return "\n".join(lines)

    def _build_sources_section(self, results: dict) -> str:
        """
        Builds the 'Sources Used' section.

        This section shows, for each agent, whether its result came from
        Gemini or from the rule-based fallback. This is important for
        transparency — it lets the student (or a Kaggle judge!) see
        exactly which parts of the report were AI-generated vs
        rule-based, demonstrating that the system is resilient even when
        Gemini fails.

        We read each agent's own "source" field directly rather than
        guessing — every agent already returns "gemini" or "fallback"
        as part of its normal output.
        """
        career_source = results.get("career_result", {}).get("source", "unknown")
        skill_gap_source = results.get("skill_gap_result", {}).get("source", "unknown")
        internship_source = results.get("internship_result", {}).get("source", "unknown")
        study_plan_source = results.get("study_plan_result", {}).get("source", "unknown")
        project_source = results.get("project_result", {}).get("source", "unknown")

        # Convert the raw "gemini"/"fallback" strings into a friendlier,
        # capitalized label for the final report (e.g. "Gemini" not "gemini").
        def label(source: str) -> str:
            if source == "gemini":
                return "GEMINI AI"
            if source == "fallback":
                return "Rule-Based Analysis"
            return source.capitalize() if source in ("gemini", "fallback") else "Unknown"

        lines = [
            "## Sources Used",
            f"Career Agent: {label(career_source)}",
            f"Skill Gap Agent: {label(skill_gap_source)}",
            f"Internship Agent: {label(internship_source)}",
            f"Study Planner Agent: {label(study_plan_source)}",
            f"Project Agent: {label(project_source)}",
        ]

        return "\n".join(lines)