from agents.career_agent import CareerAgent
from agents.skill_gap_agent import SkillGapAgent
from agents.internship_agent import InternshipAgent
from agents.study_planner_agent import StudyPlannerAgent
from agents.project_recommendation_agent import ProjectRecommendationAgent

student_profile = {
    "name": "Muhammad",
    "degree": "BS Computer Science",
    "semester": 4,
    "cgpa": 3.2,
    "skills": ["Python", "Git"],
    "interests": ["AI", "Data Science"]
}

career_agent = CareerAgent()
career_result = career_agent.run(student_profile)

print("\nCAREER RESULT:")
print(career_result)

skill_agent = SkillGapAgent()

skill_result = skill_agent.run({
    "skills": student_profile["skills"],
    "career_paths": career_result["career_paths"]
})

print("\nSKILL GAP RESULT:")
print(skill_result)

internship_agent = InternshipAgent()

internship_result = internship_agent.run({
    "career_paths": career_result["career_paths"],
    "missing_skills": skill_result["missing_skills"]
})

print("\nINTERNSHIP RESULT:")
print(internship_result)

study_agent = StudyPlannerAgent()

study_result = study_agent.run({
    "missing_skills": skill_result["missing_skills"]
})

print("\nSTUDY PLAN RESULT:")
print(study_result)

project_agent = ProjectRecommendationAgent()

project_result = project_agent.run({
    "career_paths": career_result["career_paths"],
    "missing_skills": skill_result["missing_skills"]
})

print("\nPROJECT RECOMMENDATIONS:")
print(project_result)