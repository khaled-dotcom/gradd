import sys
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.src.db.database import get_db
from backend.src.db import models
from backend.src.utils.admin_auth import require_admin
from backend.src.utils.security import (
    sanitize_input, validate_search_query, validate_integer_id,
    check_rate_limit, validate_string_length
)
from backend.src.utils.search_intelligence import intelligent_job_search
from backend.src.config import settings
from backend.src.events.producer import publish_event
from backend.src.events.schemas import EventEnvelope, EventType, Topics


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_job(job: models.Job, *, for_admin: bool = False) -> dict:
    requirements = [req.requirement for req in job.requirements]
    disability_support = [d.name for d in job.disabilities]
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "company_name": job.company.name if job.company else None,
        "company_id": job.company_id,
        "location_city": job.location.city if job.location else None,
        "location_country": job.location.country if job.location else None,
        "employment_type": job.employment_type,
        "remote_type": job.remote_type,
        "required_skills": requirements,
        "disability_support": disability_support,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "source": job.source,
        "external_id": job.external_id,
        "source_url": job.source_url if for_admin else None,
        "apply_on_site_only": True,
        "country": job.country,
        "city": job.city,
        "is_accessible_focus": bool(job.is_accessible_focus),
        "is_active": bool(job.is_active),
        "imported_at": job.imported_at.isoformat() if job.imported_at else None,
    }


@router.post("/add_job")
def add_job(
    request: Request,
    title: str,
    description: str,
    employment_type: Optional[str] = "full-time",
    remote_type: Optional[str] = "remote",
    company_id: Optional[int] = None,
    location_id: Optional[int] = None,
    requirements: Optional[List[str]] = None,
    disabilities: Optional[List[int]] = None,
    db: Session = Depends(get_db),
):
    # Security: Input validation
    title = sanitize_input(title, max_length=255)
    if not validate_string_length(title, max_length=255, min_length=1):
        raise HTTPException(status_code=400, detail="Invalid job title")
    
    description = sanitize_input(description, max_length=5000)
    if not validate_string_length(description, max_length=5000, min_length=10):
        raise HTTPException(status_code=400, detail="Job description must be between 10 and 5000 characters")
    
    if employment_type not in ["full-time", "part-time", "contract", "internship"]:
        raise HTTPException(status_code=400, detail="Invalid employment type")
    
    if remote_type not in ["remote", "on-site", "hybrid"]:
        raise HTTPException(status_code=400, detail="Invalid remote type")
    
    if company_id and not validate_integer_id(company_id):
        raise HTTPException(status_code=400, detail="Invalid company ID")
    
    if location_id and not validate_integer_id(location_id):
        raise HTTPException(status_code=400, detail="Invalid location ID")
    
    if requirements:
        for req in requirements:
            req_sanitized = sanitize_input(req, max_length=255)
            if not validate_string_length(req_sanitized, max_length=255, min_length=1):
                raise HTTPException(status_code=400, detail="Invalid requirement format")
    
    if disabilities:
        for did in disabilities:
            if not validate_integer_id(did):
                raise HTTPException(status_code=400, detail=f"Invalid disability ID: {did}")
    company = db.query(models.Company).get(company_id) if company_id else None
    location = db.query(models.Location).get(location_id) if location_id else None

    job = models.Job(
        title=title,
        description=description,
        employment_type=employment_type,
        remote_type=remote_type,
        company=company,
        location=location,
    )
    db.add(job)
    db.flush()  # get job.id

    if requirements:
        for req in requirements:
            req_sanitized = sanitize_input(req, max_length=255)
            db.add(models.JobRequirement(job_id=job.id, requirement=req_sanitized))

    if disabilities:
        dis_objs = db.query(models.Disability).filter(models.Disability.id.in_(disabilities)).all()
        job.disabilities.extend(dis_objs)

    # Skip embedding creation since we're using Groq only
    # Embeddings are optional and can be added later if needed

    db.commit()
    db.refresh(job)
    if settings.EVENTS_ENABLED:
        publish_event(
            Topics.JOB,
            EventEnvelope(
                event_type=EventType.JOB_CREATED.value,
                payload={"job_id": job.id},
            ),
        )
    return {"job_id": job.id, "message": "Job created and embedded"}


@router.post("/search_jobs")
def search_jobs(
    request: Request,
    user_id: Optional[int] = None,
    disability_ids: Optional[List[int]] = None,
    disability_id: Optional[int] = None,
    skills: Optional[List[str]] = None,
    skill_id: Optional[int] = None,
    query: Optional[str] = None,
    employment_type: Optional[str] = None,
    remote_type: Optional[str] = None,
    accessible_only: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    # Security: Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"search_{client_ip}", max_requests=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    # Security: Input validation
    if query:
        query = sanitize_input(query, max_length=200)
        if not validate_search_query(query):
            raise HTTPException(status_code=400, detail="Invalid search query")
    
    if user_id and not validate_integer_id(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    if disability_id and not validate_integer_id(disability_id):
        raise HTTPException(status_code=400, detail="Invalid disability ID")
    
    if employment_type and not validate_string_length(employment_type, max_length=50):
        raise HTTPException(status_code=400, detail="Invalid employment type")
    
    if remote_type and not validate_string_length(remote_type, max_length=50):
        raise HTTPException(status_code=400, detail="Invalid remote type")
    
    # Handle single ID parameters
    if disability_id and not disability_ids:
        disability_ids = [disability_id]
    
    # Handle skill_id - convert to skill_ids list
    skill_ids = None
    if skill_id:
        if not validate_integer_id(skill_id):
            raise HTTPException(status_code=400, detail="Invalid skill ID")
        skill_ids = [skill_id]
    elif skills:
        # If skills is a list of IDs, convert to integers
        try:
            skill_ids = [int(s) for s in skills if str(s).isdigit()]
        except:
            skill_ids = None
    
    # Validate disability IDs
    if disability_ids:
        for did in disability_ids:
            if not validate_integer_id(did):
                raise HTTPException(status_code=400, detail=f"Invalid disability ID: {did}")
    
    # Validate skill IDs
    if skill_ids:
        for sid in skill_ids:
            if not validate_integer_id(sid):
                raise HTTPException(status_code=400, detail=f"Invalid skill ID: {sid}")
    
    # Get user profile if user_id provided
    user_profile = None
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user_profile = {
                "disabilities": [d.name for d in user.disabilities],
                "skills": [s.name for s in user.skills],
                "location": user.location,
                "preferred_job_type": user.preferred_job_type,
            }
    
    # Use intelligent search
    results = intelligent_job_search(
        db=db,
        query=query,
        disability_ids=disability_ids,
        skill_ids=skill_ids,
        employment_type=employment_type,
        remote_type=remote_type,
        accessible_only=bool(accessible_only),
        user_profile=user_profile,
        limit=100
    )

    return {"results": results, "count": len(results)}


@router.get("/")
def get_all_jobs(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    accessible_only: Optional[bool] = False,
    active_only: Optional[bool] = True,
    admin_user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get all jobs with pagination (optimized with eager loading)"""
    for_admin = False
    if admin_user_id is not None:
        require_admin(admin_user_id, db)
        for_admin = True

    q = db.query(models.Job).options(
        joinedload(models.Job.company),
        joinedload(models.Job.location),
        selectinload(models.Job.requirements),
        selectinload(models.Job.disabilities),
    )
    if active_only:
        q = q.filter(or_(models.Job.is_active == True, models.Job.is_active.is_(None)))
    if accessible_only:
        q = q.filter(models.Job.is_accessible_focus == True)
    jobs = q.offset(offset).limit(limit).all()
    
    results = [_serialize_job(job, for_admin=for_admin) for job in jobs]
    return {"results": results, "count": len(results)}


@router.get("/import/dashboard")
def import_dashboard(
    admin_user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Admin: jobs import stats + application counts (proof apply is on-site)."""
    require_admin(admin_user_id, db)

    active_filter = or_(models.Job.is_active == True, models.Job.is_active.is_(None))
    total_active = db.query(models.Job).filter(active_filter).count()
    by_source = (
        db.query(models.Job.source, func.count(models.Job.id))
        .filter(active_filter)
        .group_by(models.Job.source)
        .all()
    )
    total_applications = db.query(models.JobApplication).count()
    pending_applications = (
        db.query(models.JobApplication)
        .filter(models.JobApplication.status == "pending")
        .count()
    )

    run = (
        db.query(models.ImportRun)
        .order_by(models.ImportRun.started_at.desc())
        .first()
    )
    last_run = None
    if run:
        last_run = {
            "run_id": run.run_id,
            "status": run.status,
            "added": run.added,
            "updated": run.jobs_updated,
            "deactivated": run.deactivated,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "errors": run.errors,
        }

    return {
        "total_active_jobs": total_active,
        "jobs_by_source": {str(s or "manual"): c for s, c in by_source},
        "total_applications": total_applications,
        "pending_applications": pending_applications,
        "apply_on_site_only": True,
        "auto_schedule": "0 */8 * * * (Airflow DAG empowerwork_software_jobs_pipeline)",
        "last_import_run": last_run,
    }


@router.get("/accessible")
def get_accessible_jobs(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db),
):
    """Jobs flagged as disability-inclusive (imported or manual)."""
    return get_all_jobs(
        limit=limit, offset=offset, accessible_only=True, active_only=True, db=db
    )


@router.get("/import/status")
def import_status(
    admin_user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Last data-engineering pipeline run (admin only)."""
    require_admin(admin_user_id, db)
    run = (
        db.query(models.ImportRun)
        .order_by(models.ImportRun.started_at.desc())
        .first()
    )
    if not run:
        return {"status": "no_runs"}
    return {
        "run_id": run.run_id,
        "status": run.status,
        "added": run.added,
        "updated": run.jobs_updated,
        "deactivated": run.deactivated,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "errors": run.errors,
    }


@router.post("/import/trigger")
def import_trigger(
    admin_user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Run medallion pipeline (admin only). Long-running."""
    require_admin(admin_user_id, db)
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    script = root / "data-engineering" / "pipeline" / "run.py"
    if not script.exists():
        script = root / "data-engineering" / "scripts" / "run_pipeline.py"
    subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(root),
    )
    return {"status": "started", "message": "Pipeline running in background"}


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a single job by ID"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


@router.put("/{job_id}")
def update_job(
    job_id: int,
    request: Request,
    title: str,
    description: str,
    employment_type: Optional[str] = None,
    remote_type: Optional[str] = None,
    company_id: Optional[int] = None,
    location_id: Optional[int] = None,
    requirements: Optional[List[str]] = None,
    disabilities: Optional[List[int]] = None,
    db: Session = Depends(get_db),
):
    """Update a job"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Security: Input validation
    title = sanitize_input(title, max_length=255)
    if not validate_string_length(title, max_length=255, min_length=1):
        raise HTTPException(status_code=400, detail="Invalid job title")
    
    description = sanitize_input(description, max_length=5000)
    if not validate_string_length(description, max_length=5000, min_length=10):
        raise HTTPException(status_code=400, detail="Job description must be between 10 and 5000 characters")
    
    # Update job fields
    job.title = title
    job.description = description
    
    if employment_type:
        if employment_type not in ["full-time", "part-time", "contract", "internship"]:
            raise HTTPException(status_code=400, detail="Invalid employment type")
        job.employment_type = employment_type
    
    if remote_type:
        if remote_type not in ["remote", "on-site", "hybrid"]:
            raise HTTPException(status_code=400, detail="Invalid remote type")
        job.remote_type = remote_type
    
    if company_id:
        company = db.query(models.Company).get(company_id)
        if company:
            job.company = company
    
    if location_id:
        location = db.query(models.Location).get(location_id)
        if location:
            job.location = location
    
    # Update requirements
    if requirements is not None:
        # Delete old requirements
        db.query(models.JobRequirement).filter(models.JobRequirement.job_id == job_id).delete()
        # Add new requirements
        for req in requirements:
            req_sanitized = sanitize_input(req, max_length=255)
            db.add(models.JobRequirement(job_id=job.id, requirement=req_sanitized))
    
    # Update disabilities
    if disabilities is not None:
        job.disabilities.clear()
        if disabilities:
            dis_objs = db.query(models.Disability).filter(models.Disability.id.in_(disabilities)).all()
            job.disabilities.extend(dis_objs)
    
    db.commit()
    db.refresh(job)
    if settings.EVENTS_ENABLED:
        publish_event(
            Topics.JOB,
            EventEnvelope(
                event_type=EventType.JOB_UPDATED.value,
                payload={"job_id": job.id},
            ),
        )
    return {"job_id": job.id, "message": "Job updated successfully"}


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a job"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    if settings.EVENTS_ENABLED:
        publish_event(
            Topics.JOB,
            EventEnvelope(
                event_type=EventType.JOB_DELETED.value,
                payload={"job_id": job_id},
            ),
        )
    return {"message": "Job deleted successfully"}

