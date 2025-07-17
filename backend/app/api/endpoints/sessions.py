# # sessions.py
# import uuid
# from datetime import datetime, timezone
# from fastapi import APIRouter, Depends, HTTPException
# from sqlmodel import Session, select, func
# from app.auth.dependencies import get_current_user
# from app.core.database import get_session
# from app.models.db import User, UserSession, UserQuery
# from app.models.schemas import SessionCreateResponse, SessionListResponse, SessionResponse, SessionUpdateRequest

# router = APIRouter(prefix="/sessions", tags=["sessions"])

# @router.post("", response_model=SessionCreateResponse)
# async def create_session(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_session)
# ):
#     """Create a new user session"""
#     session_id = uuid.uuid4().hex
    
#     user_session = UserSession(
#         session_id=session_id,
#         user_id=current_user.id,
#         created_at=datetime.now(timezone.utc),
#         is_active=True
#     )
    
#     db.add(user_session)
#     db.commit()
#     db.refresh(user_session)
    
#     return SessionCreateResponse(session_id=session_id, created_at=user_session.created_at)

# @router.get("", response_model=SessionListResponse)
# async def list_sessions(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_session)
# ):
#     """List all sessions for the current user"""
#     statement = select(UserSession).where(
#         UserSession.user_id == current_user.id
#     )
#     sessions = db.exec(statement).all()
    
#     return SessionListResponse(
#         sessions=[{"session_id": s.session_id, "created_at": s.created_at} for s in sessions]
#     )

# # @router.delete("/{session_id}")
# # async def delete_session(
# #     session_id: str,
# #     current_user: User = Depends(get_current_user),
# #     db: Session = Depends(get_session)
# # ):
# #     """Delete/deactivate a user session"""
# #     statement = select(UserSession).where(
# #         UserSession.session_id == session_id,
# #         UserSession.user_id == current_user.id
# #     )
# #     session = db.exec(statement).first()
    
# #     if not session:
# #         raise HTTPException(status_code=404, detail="Session not found")
    
# #     session.is_active = False
# #     db.add(session)
# #     db.commit()
    
# #     return {"message": "Session deactivated"}

# @router.get("/{session_id}", response_model=SessionResponse)
# async def get_session(
#     session_id: str,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_session)
# ):
#     """Get details of a specific session"""
#     # Get session with query count
#     statement = (
#         select(
#             UserSession.session_id,
#             UserSession.created_at,
#             UserSession.last_activity,
#             func.count(UserQuery.id).label("query_count")
#         )
#         .outerjoin(UserQuery, UserSession.session_id == UserQuery.session_id)
#         .where(
#             UserSession.session_id == session_id,
#             UserSession.user_id == current_user.id,
#             # UserSession.is_active == True
#         )
#         .group_by(UserSession.session_id, UserSession.created_at, UserSession.last_activity)
#     )
    
#     result = db.exec(statement).first()
    
#     if not result:
#         raise HTTPException(status_code=404, detail="Session not found")
    
#     return SessionResponse(
#         session_id=result.session_id,
#         created_at=result.created_at,
#         last_activity=result.last_activity or result.created_at,
#         query_count=result.query_count or 0
#     )

# @router.delete("/{session_id}")
# async def delete_session(
#     session_id: str,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_session)
# ):
#     statement = select(UserSession).where(
#         UserSession.session_id == session_id,
#         UserSession.user_id == current_user.id
#     )
#     Session = db.exec(statement).first()
#     if not Session:
#         raise HTTPException(status_code=404, detail="Session not found")

#     try:
#         db.delete(Session)
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error deleting session {session_id}: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")

#     return {"message": "Session deleted"}



# sessions.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.auth.dependencies import get_current_user
from app.core.database import get_session
from app.models.db import User, UserSession, UserQuery
from app.models.schemas import SessionCreateResponse, SessionListResponse, SessionResponse, SessionUpdateRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionCreateResponse)
async def create_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Create a new user session"""
    session_id = uuid.uuid4().hex
    
    user_session = UserSession(
        session_id=session_id,
        user_id=current_user.id,
        created_at=datetime.now(timezone.utc),
        is_active=True
    )
    
    db.add(user_session)
    db.commit()
    db.refresh(user_session)
    
    return SessionCreateResponse(session_id=session_id, created_at=user_session.created_at)

@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """List all sessions for the current user"""
    statement = select(UserSession).where(
        UserSession.user_id == current_user.id
    )
    sessions = db.exec(statement).all()
    
    return SessionListResponse(
        sessions=[{"session_id": s.session_id, "created_at": s.created_at} for s in sessions]
    )

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Delete/deactivate a user session"""
    statement = select(UserSession).where(
        UserSession.session_id == session_id,
        UserSession.user_id == current_user.id
    )
    session = db.exec(statement).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deactivated"}

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get details of a specific session"""
    # Get session with query count
    statement = (
        select(
            UserSession.session_id,
            UserSession.created_at,
            UserSession.last_activity,
            func.count(UserQuery.id).label("query_count")
        )
        .outerjoin(UserQuery, UserSession.session_id == UserQuery.session_id)
        .where(
            UserSession.session_id == session_id,
            UserSession.user_id == current_user.id,
            # UserSession.is_active == True
        )
        .group_by(UserSession.session_id, UserSession.created_at, UserSession.last_activity)
    )
    
    result = db.exec(statement).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=result.session_id,
        created_at=result.created_at,
        last_activity=result.last_activity or result.created_at,
        query_count=result.query_count or 0
    )