from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    role = Column(String, default="student")  # student / reviewer / faculty



class PlagiarismJob(Base):
    __tablename__ = "plagiarism_jobs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("research_projects.id"), nullable=False)

    file_path = Column(String, nullable=False)
    report_path = Column(String, nullable=True)

    status = Column(String, default="queued")  
    # queued | processing | completed | failed

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    abstract = Column(Text, nullable=False)
    domain = Column(String, nullable=False)
    visibility = Column(String, default="private")

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("research_projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    role = Column(String, default="co-author")
    is_accepted = Column(Boolean, default=False)

    user = relationship("User")
    project = relationship("ResearchProject")


class PaperDraft(Base):
    __tablename__ = "paper_drafts"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("research_projects.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ResearchProject")
    author = relationship("User")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("research_projects.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    score = Column(Integer, nullable=False)
    comments = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ResearchProject")
    reviewer = relationship("User")

class ReviewAssignment(Base):
    __tablename__ = "review_assignments"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("research_projects.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    assigned_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ResearchProject", foreign_keys=[project_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    editor = relationship("User", foreign_keys=[assigned_by])
