from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from models import PaperDraft
from schemas import DraftCreate, DraftResponse
from sqlalchemy import func
from schemas import UserResponse
from database import engine, SessionLocal
import models
from schemas import InviteMember, RespondInvite, ProjectMemberResponse
from models import (
    User,
    ResearchProject,
    ProjectMember,
    PlagiarismJob,
)
from schemas import UserCreate, UserLogin, ProjectCreate, ProjectResponse
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from models import Review
from schemas import ReviewCreate, ReviewResponse
from models import ReviewAssignment
from schemas import AssignReviewer, AssignmentResponse
from fastapi import UploadFile, File
import os
import uuid

# ----------------------------------------
# Create database tables
# ----------------------------------------
models.Base.metadata.create_all(bind=engine)

# ----------------------------------------
# Create FastAPI app
# ----------------------------------------
app = FastAPI(
    title="AcadFlow API",
    description="Research workflow, review & plagiarism platform",
    version="1.0.0"
)



# ----------------------------------------
# Database dependency
# ----------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------
# Root
# ----------------------------------------
@app.get("/")
def root():
    return {"message": "AcadFlow backend running 🚀"}


# ----------------------------------------
# Signup
# ----------------------------------------
@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)

    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_pw,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


# ----------------------------------------
# Login
# ----------------------------------------
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(
        user.password, db_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=timedelta(minutes=60),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ----------------------------------------
# Current user
# ----------------------------------------


@app.get("/me", response_model=UserResponse)
def read_current_user(
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@app.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if role not in ["student", "reviewer", "faculty"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    current_user = db.query(User).filter(
        User.email == current_user_email
    ).first()

    if current_user.role != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can change roles",
        )

    target_user = db.query(User).filter(User.id == user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.role = role
    db.commit()

    return {
        "message": f"User role updated to {role}"
    }


# ----------------------------------------
# Create Research Project
# ----------------------------------------
@app.post("/projects", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_project = ResearchProject(
    title=project.title,
    abstract=project.abstract,
    domain=project.domain,
    visibility=project.visibility,
    owner_id=user.id,
)


    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # ✅ Add owner as project member
    owner_member = ProjectMember(
        project_id=new_project.id,
        user_id=user.id,
        role="owner",
        is_accepted=True,
    )

    db.add(owner_member)
    db.commit()

    return new_project


# ----------------------------------------
# Get My Projects
# ----------------------------------------
@app.get("/projects", response_model=list[ProjectResponse])
def get_my_projects(
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    projects = (
        db.query(ResearchProject)
        .filter(ResearchProject.owner_id == user.id)
        .all()
    )

    return projects


@app.post("/projects/invite")
def invite_member(
    invite: InviteMember,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inviter = db.query(User).filter(User.email == current_user_email).first()
    project = db.query(ResearchProject).filter(
        ResearchProject.id == invite.project_id
    ).first()
    invitee = db.query(User).filter(User.email == invite.email).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != inviter.id:
        raise HTTPException(status_code=403, detail="Only owner can invite")

    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == invitee.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already invited or member",
        )

    invitation = ProjectMember(
        project_id=project.id,
        user_id=invitee.id,
        role="co-author",
        is_accepted=False,
    )

    db.add(invitation)
    db.commit()

    return {"message": "Invitation sent"}
@app.post("/projects/respond")
def respond_to_invite(
    response: RespondInvite,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == response.project_id,
        ProjectMember.user_id == user.id,
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if response.accept:
        membership.is_accepted = True
        db.commit()
        return {"message": "Invitation accepted"}
    else:
        db.delete(membership)
        db.commit()
        return {"message": "Invitation rejected"}
@app.get("/projects/{project_id}/members", response_model=list[ProjectMemberResponse])
def get_project_members(
    project_id: int,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()
    project = db.query(ResearchProject).filter(
        ResearchProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only members can view members list
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
        ProjectMember.is_accepted == True,
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")

    members = (
        db.query(ProjectMember)
        .join(User)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.is_accepted == True,
        )
        .all()
    )

    return [
        ProjectMemberResponse(
            id=m.user.id,
            name=m.user.name,
            email=m.user.email,
            role=m.role,
        )
        for m in members
    ]

@app.put("/projects/{project_id}/visibility")
def update_project_visibility(
    project_id: int,
    visibility: str,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if visibility not in ["public", "private"]:
        raise HTTPException(status_code=400, detail="Invalid visibility")

    user = db.query(User).filter(User.email == current_user_email).first()
    project = db.query(ResearchProject).filter(
        ResearchProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only owner can change visibility")

    project.visibility = visibility
    db.commit()

    return {"message": f"Project set to {visibility}"}

@app.get("/projects/public", response_model=list[ProjectResponse])
def get_public_projects(db: Session = Depends(get_db)):
    projects = db.query(ResearchProject).filter(
        ResearchProject.visibility == "public"
    ).all()

    return projects

@app.post("/drafts", response_model=DraftResponse)
def create_draft(
    draft: DraftCreate,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    # Check project
    project = db.query(ResearchProject).filter(
        ResearchProject.id == draft.project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check membership
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
        ProjectMember.is_accepted == True,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")

    # Get next version number
    last_version = db.query(func.max(PaperDraft.version)).filter(
        PaperDraft.project_id == project.id
    ).scalar()

    next_version = 1 if last_version is None else last_version + 1

    new_draft = PaperDraft(
        project_id=project.id,
        created_by=user.id,
        version=next_version,
        content=draft.content,
    )

    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)

    return new_draft
@app.get("/projects/{project_id}/drafts", response_model=list[DraftResponse])
def get_project_drafts(
    project_id: int,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    # Check membership
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id,
        ProjectMember.is_accepted == True,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    drafts = (
        db.query(PaperDraft)
        .filter(PaperDraft.project_id == project_id)
        .order_by(PaperDraft.version)
        .all()
    )

    return drafts
@app.post("/reviews", response_model=ReviewResponse)
def submit_review(
    review: ReviewCreate,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reviewer = db.query(User).filter(User.email == current_user_email).first()

    if reviewer.role not in ["reviewer", "faculty"]:
        raise HTTPException(
            status_code=403,
            detail="Only reviewers or faculty can submit reviews",
        )

    project = db.query(ResearchProject).filter(
        ResearchProject.id == review.project_id,
        ResearchProject.visibility == "public",
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found or not open for review",
        )

    existing = db.query(Review).filter(
        Review.project_id == project.id,
        Review.reviewer_id == reviewer.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this project",
        )

    new_review = Review(
        project_id=project.id,
        reviewer_id=reviewer.id,
        score=review.score,
        comments=review.comments,
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return new_review

@app.get("/projects/{project_id}/reviews", response_model=list[ReviewResponse])
def get_project_reviews(
    project_id: int,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    # Must be project owner or faculty
    project = db.query(ResearchProject).filter(
        ResearchProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != user.id and user.role != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    reviews = db.query(Review).filter(
        Review.project_id == project.id
    ).all()

    return reviews
@app.post("/assign-reviewer", response_model=AssignmentResponse)
def assign_reviewer(
    data: AssignReviewer,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    editor = db.query(User).filter(User.email == current_user_email).first()

    # Only faculty can assign reviewers
    if editor.role != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can assign reviewers",
        )

    reviewer = db.query(User).filter(
        User.email == data.reviewer_email
    ).first()

    if not reviewer or reviewer.role != "reviewer":
        raise HTTPException(
            status_code=404,
            detail="Reviewer not found or not a reviewer",
        )

    project = db.query(ResearchProject).filter(
        ResearchProject.id == data.project_id
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    existing = db.query(ReviewAssignment).filter(
        ReviewAssignment.project_id == project.id,
        ReviewAssignment.reviewer_id == reviewer.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Reviewer already assigned",
        )

    assignment = ReviewAssignment(
        project_id=project.id,
        reviewer_id=reviewer.id,
        assigned_by=editor.id,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment
@app.post("/plagiarism/upload")
def upload_for_plagiarism(
    project_id: int,
    file: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    project = db.query(ResearchProject).filter(
        ResearchProject.id == project_id
    ).first()

    if not project or project.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only project owner can upload",
        )

    # Validate file type
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF or DOCX allowed",
        )

    # Save file
    os.makedirs("uploads/submissions", exist_ok=True)
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join("uploads/submissions", unique_name)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # Create plagiarism job
    job = PlagiarismJob(
        user_id=user.id,
        project_id=project.id,
        file_path=file_path,
        status="queued",
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status,
        "eta": "6 hours",
        "message": "File uploaded successfully",
    }
@app.get("/admin/plagiarism/jobs")
def list_plagiarism_jobs(
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = db.query(User).filter(
        User.email == current_user_email
    ).first()

    if admin.role != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Admin access only",
        )

    jobs = db.query(PlagiarismJob).all()

    return jobs

@app.post("/admin/plagiarism/{job_id}/upload-report")
def upload_plagiarism_report(
    job_id: int,
    report: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = db.query(User).filter(
        User.email == current_user_email
    ).first()

    if admin.role != "faculty":
        raise HTTPException(status_code=403)

    job = db.query(PlagiarismJob).filter(
        PlagiarismJob.id == job_id
    ).first()

    if not job:
        raise HTTPException(status_code=404)

    os.makedirs("uploads/reports", exist_ok=True)
    report_path = f"uploads/reports/{uuid.uuid4()}_{report.filename}"

    with open(report_path, "wb") as f:
        f.write(report.file.read())

    job.report_path = report_path
    job.status = "completed"
    job.completed_at = datetime.utcnow()

    db.commit()

    return {"message": "Report uploaded successfully"}

@app.get("/plagiarism/{job_id}/status")
def check_plagiarism_status(
    job_id: int,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    job = db.query(PlagiarismJob).filter(
        PlagiarismJob.id == job_id,
        PlagiarismJob.user_id == user.id,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "completed_at": job.completed_at,
    }

from fastapi.responses import FileResponse
import os

@app.get("/plagiarism/{job_id}/report")
def download_plagiarism_report(
    job_id: int,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()

    job = db.query(PlagiarismJob).filter(
        PlagiarismJob.id == job_id,
        PlagiarismJob.user_id == user.id,
        PlagiarismJob.status == "completed",
    ).first()

    if not job or not job.report_path:
        raise HTTPException(
            status_code=404,
            detail="Report not available yet",
        )

    if not os.path.exists(job.report_path):
        raise HTTPException(
            status_code=500,
            detail="Report file missing",
        )

    return FileResponse(
        job.report_path,
        media_type="application/pdf",
        filename=os.path.basename(job.report_path),
    )
