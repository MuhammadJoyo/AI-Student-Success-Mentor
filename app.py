from agents.career_agent import CareerAgent
from agents.skill_gap_agent import SkillGapAgent
from agents.internship_agent import InternshipAgent

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