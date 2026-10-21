from pydantic import BaseModel


class AlumnoCreate(BaseModel):
    nombre: str


class AlumnoUpdate(BaseModel):
    nombre: str


class MateriaCreate(BaseModel):
    nombre: str


class MateriaUpdate(BaseModel):
    nombre: str


# ==================================================
# PRODUCTOS
# ==================================================

from decimal import Decimal

from pydantic import ConfigDict, Field
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, index=True)
    descripcion = Column(String(255), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)


class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str = Field(..., min_length=1, max_length=255)
    precio: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(..., ge=0)


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(ProductoBase):
    pass


class ProductoResponse(ProductoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ==================================================
# ACTIVIDAD 3: EMPRESAS Y USUARIOS
# ==================================================


def utc_now():
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, index=True)
    legal_name = Column(String(180))
    tax_id = Column(String(30), unique=True)
    email = Column(String(254))
    phone = Column(String(30))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    memberships = relationship("CompanyUser", back_populates="company")
    accounts = relationship("Account", back_populates="company")
    concepts = relationship("Concept", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    memberships = relationship("CompanyUser", back_populates="user")


class CompanyUser(Base):
    __tablename__ = "company_users"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    company = relationship("Company", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    role_assignments = relationship("CompanyUserRole", back_populates="company_user")


# ==================================================
# ACTIVIDAD 4: CUENTAS, CONCEPTOS Y MOVIMIENTOS
# ==================================================


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_account_company_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    account_type = Column(String(20), nullable=False)
    name = Column(String(120), nullable=False)
    bank_name = Column(String(120))
    account_number = Column(String(50))
    clabe = Column(String(18))
    card_last_digits = Column(String(4))
    short_description = Column(String(255))
    long_description = Column(String(1000))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    company = relationship("Company", back_populates="accounts")
    allowed_concepts = relationship("AccountConcept", back_populates="account")


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("company_id", "concept_type", "name", name="uq_concept_company_type_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_type = Column(String(10), nullable=False)
    name = Column(String(120), nullable=False)
    short_description = Column(String(255))
    long_description = Column(String(1000))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    company = relationship("Company", back_populates="concepts")
    allowed_accounts = relationship("AccountConcept", back_populates="concept")


class AccountConcept(Base):
    __tablename__ = "account_concepts"
    __table_args__ = (
        UniqueConstraint("account_id", "concept_id", name="uq_account_concept"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    account = relationship("Account", back_populates="allowed_concepts")
    concept = relationship("Concept", back_populates="allowed_accounts")


class FinancialTransaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False, index=True)
    transaction_type = Column(String(10), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    captured_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    captured_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    short_description = Column(String(255))
    long_description = Column(String(1000))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    account = relationship("Account")
    concept = relationship("Concept")
    captured_by_user = relationship("User")


# ==================================================
# ACTIVIDAD 5: ROLES Y PERMISOS (RBAC plano)
# ==================================================


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    permissions = relationship("RolePermission", back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    roles = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class CompanyUserRole(Base):
    __tablename__ = "company_user_roles"
    __table_args__ = (
        UniqueConstraint("company_user_id", "role_id", name="uq_company_user_role"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_user_id = Column(Integer, ForeignKey("company_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    company_user = relationship("CompanyUser", back_populates="role_assignments")
    role = relationship("Role")
