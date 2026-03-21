from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.bd.database import get_db
from backend.bd.models import Company, User
from backend.schemas import CompanyCreate, CompanyRead
from backend.services.permissions import PermissionCode, require_permissions

router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("/", response_model=list[CompanyRead])
def get_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.COMPANIES_VIEW,
            PermissionCode.COMPANIES_MANAGE,
        )
    ),
):
    _ = current_user
    return db.query(Company).all()

@router.post("/", response_model=CompanyRead)
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(PermissionCode.COMPANIES_MANAGE)),
):
    _ = current_user
    db_company = Company(name=company.name)
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

@router.put("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: int,
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(PermissionCode.COMPANIES_MANAGE)),
):
    _ = current_user
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    company.name = data.name
    db.commit()
    db.refresh(company)
    return company

@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(PermissionCode.COMPANIES_MANAGE)),
):
    _ = current_user
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    db.delete(company)
    db.commit()
    return {"ok": True}
