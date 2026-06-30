from agents.career_agent import CareerAgent

student_profile = {
    "name": "Muhammad",
    "degree": "BS Computer Science",
    "semester": 4,
    "cgpa": 3.2,
    "skills": ["Python", "Git"],
    "interests": ["AI", "Data Science"]
}

agent = CareerAgent()

result = agent.run(student_profile)

print(result)