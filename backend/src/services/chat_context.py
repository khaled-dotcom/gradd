"""Build user profile and job list for RAG chat (API + workers)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload, selectinload

from backend.src.db import models
from backend.src.utils.search_intelligence import filter_jobs_for_chat


def build_user_profile(db: Session, user_id: Optional[int]) -> Optional[dict]:
    if not user_id:
        return None
    user = (
        db.query(models.User)
        .options(
            selectinload(models.User.disabilities),
            selectinload(models.User.skills),
        )
        .filter(models.User.id == user_id)
        .first()
    )
    if not user:
        return None

    applications = (
        db.query(models.JobApplication)
        .options(joinedload(models.JobApplication.job))
        .filter(models.JobApplication.user_id == user_id)
        .order_by(models.JobApplication.applied_at.desc())
        .limit(10)
        .all()
    )
    applied_job_ids = [app.job_id for app in applications]
    applied_jobs_info = []
    cv_summaries = []
    skill_names = {s.name for s in user.skills} if user.skills else set()

    for app in applications:
        if app.job:
            applied_jobs_info.append(
                {
                    "job_id": app.job_id,
                    "job_title": app.job.title,
                    "status": app.status,
                    "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                }
            )
        cv_info = app.cv_extracted_info_dict
        if cv_info and not cv_info.get("error"):
            summary = {
                "job_title": app.job.title if app.job else None,
                "cv_stored_at": app.cv_file_path,
                "name": cv_info.get("name"),
                "email": cv_info.get("email"),
                "skills": cv_info.get("skills") or [],
                "experience_years": cv_info.get("experience_years"),
                "education": (cv_info.get("education") or [])[:2],
                "raw_excerpt": (cv_info.get("raw_text") or "")[:400],
            }
            cv_summaries.append(summary)
            for sk in summary["skills"]:
                if sk:
                    skill_names.add(sk)

    return {
        "disabilities": [d.name for d in user.disabilities] if user.disabilities else [],
        "skills": sorted(skill_names),
        "location": user.location,
        "preferred_job_type": user.preferred_job_type,
        "applied_jobs": applied_jobs_info,
        "applied_job_ids": applied_job_ids,
        "cv_summaries": cv_summaries,
    }


def format_cv_context(cv_summaries: List[Dict[str, Any]]) -> str:
    """Format CV rows from job_applications (file on Azure Blob, text in DB)."""
    if not cv_summaries:
        return ""
    lines = []
    for i, cv in enumerate(cv_summaries[:3], 1):
        parts = [f"CV #{i}"]
        if cv.get("job_title"):
            parts.append(f"(application: {cv['job_title']})")
        if cv.get("name"):
            parts.append(f"Name: {cv['name']}")
        if cv.get("skills"):
            parts.append(f"Skills: {', '.join(cv['skills'][:12])}")
        if cv.get("experience_years"):
            parts.append(f"Experience: {cv['experience_years']} years")
        if cv.get("education"):
            edu = "; ".join(str(e)[:80] for e in cv["education"][:2])
            if edu:
                parts.append(f"Education: {edu}")
        if cv.get("raw_excerpt"):
            parts.append(f"Excerpt: {cv['raw_excerpt'][:300]}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def load_jobs_data(db: Session, user_profile: Optional[dict], limit: int = 50) -> List[Dict[str, Any]]:
    all_jobs = (
        db.query(models.Job)
        .options(
            joinedload(models.Job.company),
            joinedload(models.Job.location),
            selectinload(models.Job.requirements),
            selectinload(models.Job.disabilities),
        )
        .limit(limit)
        .all()
    )
    jobs_data = []
    for job in all_jobs:
        requirements = [req.requirement for req in job.requirements] if job.requirements else []
        disability_support = [d.name for d in job.disabilities] if job.disabilities else []
        has_applied = user_profile and job.id in user_profile.get("applied_job_ids", [])
        location_str = "Remote"
        if job.location:
            city = job.location.city or ""
            country = job.location.country or ""
            if city or country:
                location_str = f"{city}, {country}".strip(", ")
        jobs_data.append(
            {
                "id": job.id,
                "title": job.title or "Untitled",
                "description": job.description or "",
                "company": job.company.name if job.company else "Unknown",
                "location": location_str,
                "employment_type": job.employment_type or "full-time",
                "remote_type": job.remote_type or "remote",
                "requirements": requirements,
                "disability_support": disability_support,
                "has_applied": has_applied,
            }
        )
    return jobs_data


def prepare_chat_context(
    db: Session, message: str, user_id: Optional[int]
) -> Tuple[Optional[dict], List[Dict[str, Any]]]:
    user_profile = build_user_profile(db, user_id)
    jobs_data = load_jobs_data(db, user_profile)
    relevant = filter_jobs_for_chat(jobs_data, message, user_profile)
    return user_profile, relevant
