from hashlib import sha256
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from backend.app.database import SessionLocal
from backend.app.models.entities import Claimant, Claim, Policy, Incident, RelationshipEdge

router = APIRouter(prefix='/api/claimants', tags=['Claimant Management'])

class CreateClaimant(BaseModel):
    claimant_name: str = Field(min_length=1, max_length=150)
    age: int | None = Field(default=None, ge=0, le=120)
    address: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    status: Literal['ACTIVE', 'INACTIVE'] = 'ACTIVE'

class UpdateClaimant(BaseModel):
    claimant_name: str = Field(min_length=1, max_length=150)
    age: int | None = Field(default=None, ge=0, le=120)
    address: str | None = None
    phone: str | None = None
    status: Literal['ACTIVE', 'INACTIVE']

def hashed(value):
    return sha256(value.strip().encode('utf-8')).hexdigest()

def serialize(c):
    return {'claimant_id': c.claimant_id, 'claimant_name': c.claimant_name, 'age': c.age, 'status': c.status, 'address_hash': c.address_hash, 'phone_hash': c.phone_hash}

@router.get('')
def list_claimants(search: str = Query('', max_length=150), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with SessionLocal() as db:
        stmt = select(Claimant)
        if search.strip():
            s = f'%{search.strip()}%'
            stmt = stmt.where(or_(Claimant.claimant_id.ilike(s), Claimant.claimant_name.ilike(s)))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Claimant.claimant_id).offset(offset).limit(limit)).all()
        return {'total': total, 'items': [serialize(c) for c in rows]}

@router.post('', status_code=201)
def create_claimant(data: CreateClaimant):
    if not data.claimant_name.strip() or not data.address.strip() or not data.phone.strip():
        raise HTTPException(422, 'Name, address, and phone cannot be blank')
    with SessionLocal() as db:
        c = Claimant(claimant_id=f'CLT-{uuid4().hex[:12].upper()}', claimant_name=data.claimant_name.strip(), age=data.age, address_hash=hashed(data.address), phone_hash=hashed(data.phone), status=data.status)
        db.add(c)
        db.commit()
        db.refresh(c)
        return serialize(c)

@router.get('/{claimant_id}')
def claimant_details(claimant_id: str):
    with SessionLocal() as db:
        c = db.get(Claimant, claimant_id)
        if not c:
            raise HTTPException(404, 'Claimant not found')
        claims = db.scalars(select(Claim).where(Claim.claimant_id == claimant_id).order_by(Claim.claim_id)).all()
        return {**serialize(c), 'claims': [{'claim_id': x.claim_id, 'status': x.status, 'claimed_amount': x.claimed_amount} for x in claims]}

@router.put('/{claimant_id}')
def update_claimant(claimant_id: str, data: UpdateClaimant):
    if not data.claimant_name.strip():
        raise HTTPException(422, 'Name cannot be blank')
    with SessionLocal() as db:
        c = db.get(Claimant, claimant_id)
        if not c:
            raise HTTPException(404, 'Claimant not found')
        c.claimant_name = data.claimant_name.strip()
        c.age = data.age
        c.status = data.status
        if data.address is not None:
            if not data.address.strip():
                raise HTTPException(422, 'Address cannot be blank')
            c.address_hash = hashed(data.address)
        if data.phone is not None:
            if not data.phone.strip():
                raise HTTPException(422, 'Phone cannot be blank')
            c.phone_hash = hashed(data.phone)
        db.commit()
        db.refresh(c)
        return serialize(c)

@router.delete('/{claimant_id}')
def delete_claimant(claimant_id: str):
    with SessionLocal() as db:
        c = db.get(Claimant, claimant_id)
        if not c:
            raise HTTPException(404, 'Claimant not found')
        links = {
            'claims': db.scalar(select(func.count()).select_from(Claim).where(Claim.claimant_id == claimant_id)) or 0,
            'policies': db.scalar(select(func.count()).select_from(Policy).where(Policy.claimant_id == claimant_id)) or 0,
            'incidents': db.scalar(select(func.count()).select_from(Incident).where(Incident.claimant_id == claimant_id)) or 0,
            'network_edges': db.scalar(select(func.count()).select_from(RelationshipEdge).where(or_(
                (RelationshipEdge.source_type.ilike('CLAIMANT')) & (RelationshipEdge.source_id == claimant_id),
                (RelationshipEdge.target_type.ilike('CLAIMANT')) & (RelationshipEdge.target_id == claimant_id)
            ))) or 0,
        }
        if any(links.values()):
            raise HTTPException(409, detail={'message': 'Cannot delete claimant with linked records. Set status to INACTIVE instead.', 'linked': links})
        db.delete(c)
        db.commit()
        return {'deleted': claimant_id}
