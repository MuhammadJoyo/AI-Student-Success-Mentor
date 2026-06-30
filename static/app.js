/**
 * SuccessAI Front-End Application Logic
 * Implements Single-Page-App (SPA) view transitions, profile form submission,
 * simulated progressive loading states, results rendering, and source provenance displays.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Navigation & Section Elements
    const landingSection = document.getElementById("landing-section");
    const formSection = document.getElementById("form-section");
    const loadingSection = document.getElementById("loading-section");
    const dashboardSection = document.getElementById("dashboard-section");

    // Interactive Buttons
    const btnNavStart = document.getElementById("btn-nav-start");
    const btnHeroCta = document.getElementById("btn-hero-cta");
    const btnFormBack = document.getElementById("btn-form-back");
    const btnDashRestart = document.getElementById("btn-dash-restart");
    const navLogo = document.getElementById("nav-logo");

    // Form element
    const profileForm = document.getElementById("profile-form");

    // Initialize Lucide Icons for static elements
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // --- Page Routing / State Transitions ---
    function showSection(sectionToShow) {
        const sections = [landingSection, formSection, loadingSection, dashboardSection];
        sections.forEach(sec => {
            if (sec === sectionToShow) {
                sec.classList.remove("inactive-section");
                sec.classList.add("active-section");
            } else {
                sec.classList.remove("active-section");
                sec.classList.add("inactive-section");
            }
        });
        
        // Scroll to top of the page on view switch
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // Click events for view transitions
    btnNavStart.addEventListener("click", () => showSection(formSection));
    btnHeroCta.addEventListener("click", () => showSection(formSection));
    btnFormBack.addEventListener("click", () => showSection(landingSection));
    navLogo.addEventListener("click", () => showSection(landingSection));
    btnDashRestart.addEventListener("click", () => {
        profileForm.reset();
        showSection(formSection);
    });

    // --- Loading & Simulation Logic ---
    let progressTimer = null;
    const loadSteps = [
        document.getElementById("load-step-1"),
        document.getElementById("load-step-2"),
        document.getElementById("load-step-3"),
        document.getElementById("load-step-4"),
        document.getElementById("load-step-5")
    ];

    function resetLoadingSteps() {
        loadSteps.forEach(step => {
            step.className = "loading-step-item";
            const icon = step.querySelector("i");
            if (icon) {
                icon.setAttribute("data-lucide", "circle");
            }
        });
        if (window.lucide) window.lucide.createIcons();
    }

    function startLoadingSimulation() {
        resetLoadingSteps();
        let currentStep = 0;
        
        // Highlight first step immediately
        setActiveStep(0);

        progressTimer = setInterval(() => {
            if (currentStep < loadSteps.length - 1) {
                setCompleteStep(currentStep);
                currentStep++;
                setActiveStep(currentStep);
            }
        }, 1200); // Shift state every 1.2 seconds to simulate analysis
    }

    function setActiveStep(index) {
        if (index >= 0 && index < loadSteps.length) {
            loadSteps[index].classList.add("active");
            const icon = loadSteps[index].querySelector("i");
            if (icon) icon.setAttribute("data-lucide", "loader-2");
            if (window.lucide) window.lucide.createIcons();
        }
    }

    function setCompleteStep(index) {
        if (index >= 0 && index < loadSteps.length) {
            loadSteps[index].classList.remove("active");
            loadSteps[index].classList.add("complete");
            const icon = loadSteps[index].querySelector("i");
            if (icon) icon.setAttribute("data-lucide", "check-circle-2");
            if (window.lucide) window.lucide.createIcons();
        }
    }

    function completeAllLoadingSteps() {
        clearInterval(progressTimer);
        loadSteps.forEach(step => {
            step.classList.remove("active");
            step.classList.add("complete");
            const icon = step.querySelector("i");
            if (icon) icon.setAttribute("data-lucide", "check-circle-2");
        });
        if (window.lucide) window.lucide.createIcons();
    }

    // --- Form Submission & API Interaction ---
    profileForm.addEventListener("submit", (e) => {
        e.preventDefault();

        // Retrieve inputs
        const name = document.getElementById("student-name").value;
        const degree = document.getElementById("student-degree").value;
        const semester = document.getElementById("student-semester").value;
        const cgpa = document.getElementById("student-cgpa").value;
        const skillsRaw = document.getElementById("student-skills").value;
        const interestsRaw = document.getElementById("student-interests").value;

        // Process lists (split by comma, trim whitespace)
        const skills = skillsRaw.split(",").map(s => s.trim()).filter(s => s.length > 0);
        const interests = interestsRaw.split(",").map(i => i.trim()).filter(i => i.length > 0);

        // Prepare request payload
        const payload = {
            name,
            degree,
            semester: parseInt(semester, 10),
            cgpa: parseFloat(cgpa),
            skills,
            interests
        };

        // Transition to loader
        showSection(loadingSection);
        startLoadingSimulation();

        // Perform analysis pipeline request
        fetch("/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => {
                    throw new Error(errData.error || "Server error running analysis");
                });
            }
            return response.json();
        })
        .then(data => {
            // Fast-forward loader visual items, wait brief delay for user comfort, and show dashboard
            completeAllLoadingSteps();
            setTimeout(() => {
                renderDashboard(data);
                showSection(dashboardSection);
            }, 800);
        })
        .catch(err => {
            clearInterval(progressTimer);
            alert(`Analysis Failed: ${err.message}`);
            showSection(formSection);
        });
    });

    // --- Dashboard Rendering Logic ---
    function renderDashboard(data) {
        const profile = data.profile;
        const results = data.results;

        // 1. Update Header Subtitles
        document.getElementById("dash-student-name").textContent = profile.name;
        document.getElementById("dash-student-degree").textContent = `${profile.degree} (Sem ${profile.semester}, CGPA ${profile.cgpa})`;

        // 2. Render Sources Provenance Badges
        setSourceBadge("source-careers", results.career_result?.source);
        setSourceBadge("source-gaps", results.skill_gap_result?.source);
        setSourceBadge("source-internships", results.internship_result?.source);
        setSourceBadge("source-study", results.study_plan_result?.source);
        setSourceBadge("source-projects", results.project_result?.source);

        // 3. Render Career Recommendations
        const careersList = document.getElementById("dash-careers-list");
        careersList.innerHTML = "";
        const careerPaths = results.career_result?.career_paths || [];
        if (careerPaths.length > 0) {
            careerPaths.forEach(path => {
                const li = document.createElement("li");
                li.textContent = path;
                careersList.appendChild(li);
            });
        } else {
            careersList.innerHTML = `<p class="text-muted">No careers recommended.</p>`;
        }

        // 4. Render Skill Gap Analysis
        const gapsList = document.getElementById("dash-gaps-list");
        const gapMessage = document.getElementById("dash-gap-message");
        gapsList.innerHTML = "";
        
        const missingSkills = results.skill_gap_result?.missing_skills || [];
        if (missingSkills.length > 0) {
            gapsList.classList.remove("no-gaps");
            gapMessage.textContent = "Based on your target career, here are the critical skills you should acquire:";
            missingSkills.forEach(skill => {
                const li = document.createElement("li");
                li.textContent = skill;
                gapsList.appendChild(li);
            });
        } else {
            gapsList.classList.add("no-gaps");
            gapMessage.textContent = "Congratulations! You meet all core requirements for your chosen paths.";
            const li = document.createElement("li");
            li.textContent = "All set! No current skill gaps";
            gapsList.appendChild(li);
        }

        // 5. Render Internship Recommendations
        const internshipsList = document.getElementById("dash-internships-list");
        internshipsList.innerHTML = "";
        const internships = results.internship_result?.recommended_internships || [];
        if (internships.length > 0) {
            internships.forEach(role => {
                const item = document.createElement("div");
                item.className = "internship-item";
                item.innerHTML = `
                    <div class="intern-details">
                        <div class="intern-icon">
                            <i data-lucide="building"></i>
                        </div>
                        <div>
                            <h4>${role}</h4>
                            <p class="text-muted">Recommended Entry Role</p>
                        </div>
                    </div>
                    <span class="role-badge">Recommended Role</span>
                `;
                internshipsList.appendChild(item);
            });
        } else {
            internshipsList.innerHTML = `<p class="text-muted">No internships recommended.</p>`;
        }

        // 6. Render Study Plan Timeline
        const studyTimeline = document.getElementById("dash-study-timeline");
        studyTimeline.innerHTML = "";
        const studyPlan = results.study_plan_result?.study_plan || [];
        if (studyPlan.length > 0) {
            studyPlan.forEach(weekEntry => {
                const weekNum = weekEntry.week;
                const focus = weekEntry.focus;
                const item = document.createElement("div");
                item.className = "timeline-item";
                item.innerHTML = `
                    <div class="timeline-dot"></div>
                    <div class="timeline-week">Week ${weekNum}</div>
                    <div class="timeline-content">${focus}</div>
                `;
                studyTimeline.appendChild(item);
            });
        } else {
            studyTimeline.innerHTML = `<p class="text-muted">No study plan generated.</p>`;
        }

        // 7. Render Portfolio Projects
        const projectsList = document.getElementById("dash-projects-list");
        projectsList.innerHTML = "";
        const projects = results.project_result?.recommended_projects || [];
        if (projects.length > 0) {
            projects.forEach(project => {
                const title = project.title || "Untitled Project";
                const desc = project.description || "No description provided.";
                const card = document.createElement("div");
                card.className = "project-card";
                card.innerHTML = `
                    <h4>${title}</h4>
                    <p>${desc}</p>
                    <div class="project-badge-bar">
                        <span class="proj-badge">Portfolio Project</span>
                    </div>
                `;
                projectsList.appendChild(card);
            });
        } else {
            projectsList.innerHTML = `<p class="text-muted">No portfolio projects recommended.</p>`;
        }

        // Reinitialize Lucide Icons on dynamic elements
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    // Helper to format source provenance badge
    function setSourceBadge(badgeId, source) {
        const badge = document.getElementById(badgeId);
        if (!badge) return;
        
        badge.className = "source-badge";
        if (source === "gemini") {
            badge.classList.add("badge-gemini");
            badge.textContent = "GEMINI AI";
        } else if (source === "fallback") {
            badge.classList.add("badge-fallback");
            badge.textContent = "Rule-Based Analysis";
        } else {
            badge.textContent = source || "Unknown";
        }
    }
});
