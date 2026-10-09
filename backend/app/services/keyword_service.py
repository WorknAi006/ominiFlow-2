import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.keyword import Keyword
from app.schemas.keyword import KeywordCreate, KeywordUpdate

def list_keywords(session: Session, tenant_id: uuid.UUID) -> list[Keyword]:
    return session.query(Keyword).filter(Keyword.tenant_id == tenant_id).order_by(Keyword.created_at.desc()).all()

def get_keyword(session: Session, tenant_id: uuid.UUID, keyword_id: uuid.UUID) -> Keyword:
    keyword = session.query(Keyword).filter(Keyword.tenant_id == tenant_id, Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return keyword

def create_keyword(session: Session, tenant_id: uuid.UUID, user_id: uuid.UUID, data: KeywordCreate) -> Keyword:
    existing = session.query(Keyword).filter(
        Keyword.tenant_id == tenant_id,
        Keyword.keyword_text == data.keyword_text,
        Keyword.match_type == data.match_type,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keyword with this text and match type already exists")

    keyword = Keyword(
        tenant_id=tenant_id,
        keyword_text=data.keyword_text,
        match_type=data.match_type,
        is_active=data.is_active,
        flow_id=data.flow_id,
        reply_text=data.reply_text,
        created_by_user_id=user_id,
    )
    session.add(keyword)
    session.commit()
    session.refresh(keyword)
    return keyword

def update_keyword(session: Session, tenant_id: uuid.UUID, keyword_id: uuid.UUID, data: KeywordUpdate) -> Keyword:
    keyword = get_keyword(session, tenant_id, keyword_id)
    
    update_data = data.model_dump(exclude_unset=True)
    if "keyword_text" in update_data or "match_type" in update_data:
        check_text = update_data.get("keyword_text", keyword.keyword_text)
        check_match = update_data.get("match_type", keyword.match_type)
        
        if check_text != keyword.keyword_text or check_match != keyword.match_type:
            existing = session.query(Keyword).filter(
                Keyword.tenant_id == tenant_id,
                Keyword.keyword_text == check_text,
                Keyword.match_type == check_match,
                Keyword.id != keyword_id
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keyword with this text and match type already exists")

    for key, value in update_data.items():
        setattr(keyword, key, value)
        
    session.commit()
    session.refresh(keyword)
    return keyword

def delete_keyword(session: Session, tenant_id: uuid.UUID, keyword_id: uuid.UUID) -> None:
    keyword = get_keyword(session, tenant_id, keyword_id)
    session.delete(keyword)
    session.commit()
