"""
matcher.py
Scores a job description against the skills you actually know.
"""

import re

# Common tech/tool/skill tokens we try to detect inside job descriptions.
# Extend this list as you find gaps.
SKILL_VOCAB = [
    "python", "java", "c++", "c#", "javascript", "typescript", "react",
    "node.js", "sql", "mysql", "postgresql", "mongodb", "excel", "power bi",
    "tableau", "aws", "azure", "gcp", "docker", "kubernetes", "git",
    "machine learning", "deep learning", "nlp", "pandas", "numpy",
    "tensorflow", "pytorch", "django", "flask", "spring boot", "html",
    "css", "rest api", "linux", "spark", "hadoop", "data structures",
    "algorithms", "selenium", "django rest framework", "figma",
]


def extract_required_skills(job_description: str) -> set:
    """Pull recognizable skill tokens out of a raw job description string."""
    text = job_description.lower()
    found = set()
    for skill in SKILL_VOCAB:
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            found.add(skill)
    return found


def score_job(job_description: str, known_skills: list) -> dict:
    """
    Returns a dict: {
        'required_skills': set,
        'matched_skills': set,
        'missing_skills': set,
        'match_ratio': float (0-1)
    }
    """
    known = set(s.lower().strip() for s in known_skills)
    required = extract_required_skills(job_description)

    if not required:
        # No recognizable skills in the JD — treat as low-confidence,
        # always route to human review rather than guessing.
        return {
            "required_skills": set(),
            "matched_skills": set(),
            "missing_skills": set(),
            "match_ratio": 0.0,
        }

    matched = required & known
    missing = required - known
    ratio = len(matched) / len(required)

    return {
        "required_skills": required,
        "matched_skills": matched,
        "missing_skills": missing,
        "match_ratio": round(ratio, 2),
    }


def decide_action(match_ratio: float, auto_apply_threshold: float, min_notify_threshold: float) -> str:
    """Returns 'auto_apply', 'notify', or 'skip'."""
    if match_ratio >= auto_apply_threshold:
        return "auto_apply"
    elif match_ratio >= min_notify_threshold:
        return "notify"
    else:
        return "skip"
