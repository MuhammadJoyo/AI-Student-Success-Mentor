from orchestrator import Orchestrator

student_profile = {
    "name": "Muhammad",
    "degree": "BS Computer Science",
    "semester": 4,
    "cgpa": 3.2,
    "skills": ["Python", "Git"],
    "interests": ["AI", "Data Science"]
}

orchestrator = Orchestrator()

results = orchestrator.run(student_profile)

print("\n" + "=" * 60)
print("AI STUDENT SUCCESS MENTOR REPORT")
print("=" * 60)

print("\nCAREER RESULT:")
print(results["career_result"])

print("\nSKILL GAP RESULT:")
print(results["skill_gap_result"])

print("\nINTERNSHIP RESULT:")
print(results["internship_result"])

print("\nSTUDY PLAN RESULT:")
print(results["study_plan_result"])

print("\nPROJECT RECOMMENDATIONS:")
print(results["project_result"])

print("\n" + "=" * 60)
print("REPORT GENERATED SUCCESSFULLY")
print("=" * 60)