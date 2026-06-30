from orchestrator import Orchestrator
from report_generator import ReportGenerator

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

report_generator = ReportGenerator()
report = report_generator.generate(results)

print(report)

with open("output/report.md", "w", encoding="utf-8") as file:
    file.write(report)

print("\nReport saved successfully to output/report.md")