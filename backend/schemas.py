from pydantic import BaseModel, EmailStr
from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProjectCreate(BaseModel):
    title: str
    abstract: str
    domain: str
    visibility: str = "private"  # public / private



class ProjectResponse(BaseModel):
    id: int
    title: str
    abstract: str
    domain: str
    visibility: str

    class Config:
        from_attributes = True


from pydantic import BaseModel, EmailStr

class InviteMember(BaseModel):
    project_id: int
    email: EmailStr


class RespondInvite(BaseModel):
    project_id: int
    accept: bool


class ProjectMemberResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

from datetime import datetime

class DraftCreate(BaseModel):
    project_id: int
    content: str


class DraftResponse(BaseModel):
    id: int
    project_id: int
    version: int
    content: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    project_id: int
    score: int
    comments: str


class ReviewResponse(BaseModel):
    id: int
    project_id: int
    score: int
    comments: str
    created_at: datetime

    class Config:
        from_attributes = True




class AssignReviewer(BaseModel):
    project_id: int
    reviewer_email: EmailStr


class AssignmentResponse(BaseModel):
    id: int
    project_id: int
    reviewer_id: int
    assigned_by: int
    assigned_at: datetime

    class Config:
        from_attributes = True
