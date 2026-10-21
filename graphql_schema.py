from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import strawberry
from fastapi import Depends, Request
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from database.database import get_db
from models.models import Company as CompanyModel
from models.models import CompanyUser as CompanyUserModel
from models.models import User as UserModel
from models.models import Account as AccountModel
from models.models import AccountConcept as AccountConceptModel
from models.models import Concept as ConceptModel
from models.models import FinancialTransaction as TransactionModel
from models.models import CompanyUserRole as CompanyUserRoleModel
from models.models import Permission as PermissionModel
from models.models import Role as RoleModel
from models.models import RolePermission as RolePermissionModel
from access_control import ADMIN_ROLE_CODE, exigir_permiso
from security import create_access_token, decode_access_token, hash_password, verify_password


Time = strawberry.scalar(
    datetime,
    name="Time",
    serialize=lambda value: value.isoformat(),
    parse_value=datetime.fromisoformat,
)


def normalize_email(value: str) -> str:
    try:
        return str(TypeAdapter(EmailStr).validate_python(value)).lower()
    except ValidationError as exc:
        raise ValueError("El correo electrónico no es válido") from exc


def required_text(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field} no puede estar vacío")
    return value


@strawberry.type
class Company:
    id: strawberry.ID
    name: str
    legal_name: Optional[str]
    tax_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: Time
    updated_at: Time


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str
    email_verified: bool
    is_active: bool
    created_at: Time
    updated_at: Time


@strawberry.type
class Role:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type
class Permission:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type
class CompanyUser:
    id: strawberry.ID
    company_id: strawberry.ID
    user_id: strawberry.ID
    is_admin: bool
    is_active: bool
    joined_at: Time
    company: Company
    user: User
    role: Optional[Role]


@strawberry.type
class RolePermission:
    id: strawberry.ID
    role: Role
    permission: Permission
    is_active: bool


@strawberry.type
class CompanyUserRole:
    id: strawberry.ID
    company_user: CompanyUser
    role: Role
    is_active: bool


@strawberry.type
class AuthUser:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class AuthPayload:
    token: str
    token_type: str
    user: AuthUser


@strawberry.input
class CreateCompanyInput:
    name: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@strawberry.input
class UpdateCompanyInput:
    id: strawberry.ID
    name: Optional[str] = strawberry.UNSET
    legal_name: Optional[str] = strawberry.UNSET
    tax_id: Optional[str] = strawberry.UNSET
    email: Optional[str] = strawberry.UNSET
    phone: Optional[str] = strawberry.UNSET
    is_active: Optional[bool] = strawberry.UNSET


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class CreateCompanyAdminInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


@strawberry.input
class CreateCompanyUserInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


@strawberry.input
class CreateRoleInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input
class CreatePermissionInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input
class AssignPermissionToRoleInput:
    role_id: strawberry.ID
    permission_id: strawberry.ID


@strawberry.input
class AssignRoleInput:
    company_user_id: strawberry.ID
    role_id: strawberry.ID


@strawberry.enum
class AccountType(Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


@strawberry.enum
class ConceptType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.enum
class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.type
class Account:
    id: strawberry.ID
    company_id: strawberry.ID
    account_type: AccountType
    name: str
    bank_name: Optional[str]
    account_number: Optional[str]
    clabe: Optional[str]
    card_last_digits: Optional[str]
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: Time
    updated_at: Time
    company: Company


@strawberry.type
class Concept:
    id: strawberry.ID
    company_id: strawberry.ID
    concept_type: ConceptType
    name: str
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: Time
    updated_at: Time


@strawberry.type
class AccountConcept:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    is_active: bool
    created_at: Time
    account: Account
    concept: Concept


@strawberry.type
class Transaction:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: Time
    captured_at: Time
    captured_by: strawberry.ID
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: Time
    updated_at: Time
    account: Account
    concept: Concept
    captured_by_user: User


@strawberry.input
class CreateAccountInput:
    company_id: strawberry.ID
    account_type: AccountType
    name: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    clabe: Optional[str] = None
    card_last_digits: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@strawberry.input
class CreateConceptInput:
    company_id: strawberry.ID
    concept_type: ConceptType
    name: str
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@strawberry.input
class AssignConceptToAccountInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID


@strawberry.input
class CreateTransactionInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: Optional[Time] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


def company_type(row: CompanyModel) -> Company:
    return Company(
        id=strawberry.ID(str(row.id)), name=row.name, legal_name=row.legal_name,
        tax_id=row.tax_id, email=row.email, phone=row.phone, is_active=row.is_active,
        created_at=row.created_at, updated_at=row.updated_at,
    )


def user_type(row: UserModel) -> User:
    return User(
        id=strawberry.ID(str(row.id)), name=row.name, email=row.email,
        email_verified=row.email_verified, is_active=row.is_active,
        created_at=row.created_at, updated_at=row.updated_at,
    )


def role_type(row: RoleModel) -> Role:
    return Role(
        id=strawberry.ID(str(row.id)), code=row.code, name=row.name,
        description=row.description, is_active=row.is_active,
    )


def permission_type(row: PermissionModel) -> Permission:
    return Permission(
        id=strawberry.ID(str(row.id)), code=row.code, name=row.name,
        description=row.description, is_active=row.is_active,
    )


def role_permission_type(row: RolePermissionModel) -> RolePermission:
    return RolePermission(
        id=strawberry.ID(str(row.id)), role=role_type(row.role),
        permission=permission_type(row.permission), is_active=row.is_active,
    )


def membership_type(row: CompanyUserModel) -> CompanyUser:
    active = next((a for a in row.role_assignments if a.is_active), None)
    return CompanyUser(
        id=strawberry.ID(str(row.id)), company_id=strawberry.ID(str(row.company_id)),
        user_id=strawberry.ID(str(row.user_id)), is_admin=row.is_admin,
        is_active=row.is_active, joined_at=row.joined_at,
        company=company_type(row.company), user=user_type(row.user),
        role=role_type(active.role) if active else None,
    )


def company_user_role_type(row: CompanyUserRoleModel) -> CompanyUserRole:
    return CompanyUserRole(
        id=strawberry.ID(str(row.id)), company_user=membership_type(row.company_user),
        role=role_type(row.role), is_active=row.is_active,
    )


def account_to_graphql(row: AccountModel) -> Account:
    return Account(
        id=strawberry.ID(str(row.id)), company_id=strawberry.ID(str(row.company_id)),
        account_type=AccountType(row.account_type), name=row.name, bank_name=row.bank_name,
        account_number=row.account_number, clabe=row.clabe, card_last_digits=row.card_last_digits,
        short_description=row.short_description, long_description=row.long_description,
        is_active=row.is_active, created_at=row.created_at, updated_at=row.updated_at,
        company=company_type(row.company),
    )


def concept_to_graphql(row: ConceptModel) -> Concept:
    return Concept(
        id=strawberry.ID(str(row.id)), company_id=strawberry.ID(str(row.company_id)),
        concept_type=ConceptType(row.concept_type), name=row.name,
        short_description=row.short_description, long_description=row.long_description,
        is_active=row.is_active, created_at=row.created_at, updated_at=row.updated_at,
    )


def account_concept_to_graphql(row: AccountConceptModel) -> AccountConcept:
    return AccountConcept(
        id=strawberry.ID(str(row.id)), account_id=strawberry.ID(str(row.account_id)),
        concept_id=strawberry.ID(str(row.concept_id)), is_active=row.is_active,
        created_at=row.created_at, account=account_to_graphql(row.account), concept=concept_to_graphql(row.concept),
    )


def transaction_to_graphql(row: TransactionModel) -> Transaction:
    return Transaction(
        id=strawberry.ID(str(row.id)), account_id=strawberry.ID(str(row.account_id)),
        concept_id=strawberry.ID(str(row.concept_id)),
        transaction_type=TransactionType(row.transaction_type), amount=row.amount,
        transaction_date=row.transaction_date, captured_at=row.captured_at,
        captured_by=strawberry.ID(str(row.captured_by)), short_description=row.short_description,
        long_description=row.long_description, is_active=row.is_active,
        created_at=row.created_at, updated_at=row.updated_at,
        account=account_to_graphql(row.account), concept=concept_to_graphql(row.concept),
        captured_by_user=user_type(row.captured_by_user),
    )


def db_from(info: Info) -> Session:
    return info.context["db"]


def require(
    info: Info, actor_company_user_id: strawberry.ID, code: str, company_id=None
) -> CompanyUserModel:
    """Exige el permiso `code` a la membresía que actúa (actorCompanyUserId).

    El servidor no cree lo que el cliente declare: busca el rol de esa membresía
    y lee la matriz. Si además llega un token Bearer, debe ser del mismo usuario
    que la membresía (nadie puede actuar con la membresía de otra persona).
    """
    context = info.context
    if context.get("auth_error"):
        raise ValueError(context["auth_error"])
    membership = exigir_permiso(db_from(info), int(actor_company_user_id), code, company_id)
    current_user = context.get("current_user")
    if current_user is not None and current_user.id != membership.user_id:
        raise PermissionError("La membresía no corresponde al usuario autenticado")
    return membership


def active_company(db: Session, company_id: strawberry.ID) -> CompanyModel:
    company = db.get(CompanyModel, int(company_id))
    if company is None:
        raise ValueError("La empresa no existe")
    if not company.is_active:
        raise ValueError("La empresa está inactiva")
    return company


def get_active_company_locked(db: Session, company_id: strawberry.ID) -> CompanyModel:
    company = db.query(CompanyModel).filter(CompanyModel.id == int(company_id)).with_for_update().first()
    if company is None:
        raise ValueError("La empresa no existe")
    if not company.is_active:
        raise ValueError("La empresa está inactiva")
    return company


def create_membership(info: Info, data, is_admin: bool) -> CompanyUser:
    db = db_from(info)
    try:
        company = get_active_company_locked(db, data.company_id)
        email = normalize_email(data.email)
        if db.query(UserModel).filter(UserModel.email == email).first():
            raise ValueError("El correo electrónico ya está registrado")
        if is_admin and db.query(CompanyUserModel).filter(
            CompanyUserModel.company_id == company.id,
            CompanyUserModel.is_admin.is_(True),
            CompanyUserModel.is_active.is_(True),
        ).first():
            raise ValueError("La empresa ya tiene un administrador principal")

        user = UserModel(
            name=required_text(data.name, "El nombre"), email=email,
            password_hash=hash_password(data.password),
        )
        db.add(user)
        db.flush()
        membership = CompanyUserModel(company=company, user=user, is_admin=is_admin)
        db.add(membership)
        if is_admin:
            admin_role = db.query(RoleModel).filter(RoleModel.code == ADMIN_ROLE_CODE).first()
            if admin_role is None:
                raise ValueError("El catálogo de roles no está inicializado")
            db.flush()
            db.add(CompanyUserRoleModel(company_user_id=membership.id, role_id=admin_role.id))
        db.commit()
        db.refresh(membership)
        return membership_type(membership)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("No fue posible crear el usuario; verifica que el correo no esté duplicado") from exc
    except Exception:
        db.rollback()
        raise


@strawberry.type
class Query:
    @strawberry.field
    def companies(self, info: Info, active_only: Optional[bool] = None) -> list[Company]:
        query = db_from(info).query(CompanyModel)
        if active_only:
            query = query.filter(CompanyModel.is_active.is_(True))
        return [company_type(row) for row in query.order_by(CompanyModel.id).all()]

    @strawberry.field
    def company(self, info: Info, id: strawberry.ID) -> Optional[Company]:
        row = db_from(info).get(CompanyModel, int(id))
        return company_type(row) if row else None

    @strawberry.field
    def company_users(
        self, info: Info, company_id: strawberry.ID, actor_company_user_id: strawberry.ID
    ) -> list[CompanyUser]:
        db = db_from(info)
        require(info, actor_company_user_id, "company.users.read", company_id)
        if db.get(CompanyModel, int(company_id)) is None:
            raise ValueError("La empresa no existe")
        rows = db.query(CompanyUserModel).options(
            joinedload(CompanyUserModel.company), joinedload(CompanyUserModel.user)
        ).filter(CompanyUserModel.company_id == int(company_id)).order_by(CompanyUserModel.id).all()
        return [membership_type(row) for row in rows]

    @strawberry.field
    def accounts(
        self, info: Info, company_id: strawberry.ID, actor_company_user_id: strawberry.ID,
        account_type: Optional[AccountType] = strawberry.UNSET,
        active_only: Optional[bool] = None,
    ) -> list[Account]:
        db = db_from(info)
        require(info, actor_company_user_id, "accounts.read", company_id)
        active_company(db, company_id)
        query = db.query(AccountModel).options(joinedload(AccountModel.company)).filter(
            AccountModel.company_id == int(company_id)
        )
        if account_type is not strawberry.UNSET and account_type is not None:
            query = query.filter(AccountModel.account_type == account_type.value)
        if active_only:
            query = query.filter(AccountModel.is_active.is_(True))
        return [account_to_graphql(row) for row in query.order_by(AccountModel.id).all()]

    @strawberry.field
    def concepts(
        self, info: Info, company_id: strawberry.ID, actor_company_user_id: strawberry.ID,
        concept_type: Optional[ConceptType] = strawberry.UNSET,
        active_only: Optional[bool] = None,
    ) -> list[Concept]:
        db = db_from(info)
        require(info, actor_company_user_id, "concepts.read", company_id)
        active_company(db, company_id)
        query = db.query(ConceptModel).filter(ConceptModel.company_id == int(company_id))
        if concept_type is not strawberry.UNSET and concept_type is not None:
            query = query.filter(ConceptModel.concept_type == concept_type.value)
        if active_only:
            query = query.filter(ConceptModel.is_active.is_(True))
        return [concept_to_graphql(row) for row in query.order_by(ConceptModel.id).all()]

    @strawberry.field
    def account_concepts(
        self, info: Info, account_id: strawberry.ID, actor_company_user_id: strawberry.ID
    ) -> list[AccountConcept]:
        db = db_from(info)
        account = db.get(AccountModel, int(account_id))
        if account is None:
            raise ValueError("La cuenta no existe")
        require(info, actor_company_user_id, "concepts.read", account.company_id)
        rows = db.query(AccountConceptModel).options(
            joinedload(AccountConceptModel.account).joinedload(AccountModel.company),
            joinedload(AccountConceptModel.concept),
        ).filter(AccountConceptModel.account_id == account.id).order_by(AccountConceptModel.id).all()
        return [account_concept_to_graphql(row) for row in rows]

    @strawberry.field
    def transactions(
        self, info: Info, actor_company_user_id: strawberry.ID,
        account_id: Optional[strawberry.ID] = None,
        transaction_type: Optional[TransactionType] = strawberry.UNSET,
        limit: Optional[int] = 50, offset: Optional[int] = 0,
    ) -> list[Transaction]:
        db = db_from(info)
        actor = require(info, actor_company_user_id, "transactions.read")
        if limit is None:
            limit = 50
        if offset is None:
            offset = 0
        if limit < 1 or limit > 100 or offset < 0:
            raise ValueError("limit debe estar entre 1 y 100 y offset no puede ser negativo")
        # Solo movimientos de la empresa de la membresía que consulta.
        query = db.query(TransactionModel).join(AccountModel).options(
            joinedload(TransactionModel.account).joinedload(AccountModel.company),
            joinedload(TransactionModel.concept), joinedload(TransactionModel.captured_by_user),
        ).filter(AccountModel.company_id == actor.company_id)
        if account_id is not None:
            query = query.filter(TransactionModel.account_id == int(account_id))
        if transaction_type is not strawberry.UNSET and transaction_type is not None:
            query = query.filter(TransactionModel.transaction_type == transaction_type.value)
        rows = query.order_by(TransactionModel.transaction_date.desc(), TransactionModel.id.desc()).offset(offset).limit(limit).all()
        return [transaction_to_graphql(row) for row in rows]


    @strawberry.field
    def roles(self, info: Info, active_only: Optional[bool] = None) -> list[Role]:
        query = db_from(info).query(RoleModel)
        if active_only:
            query = query.filter(RoleModel.is_active.is_(True))
        return [role_type(row) for row in query.order_by(RoleModel.id).all()]

    @strawberry.field
    def role(self, info: Info, id: strawberry.ID) -> Optional[Role]:
        row = db_from(info).get(RoleModel, int(id))
        return role_type(row) if row else None

    @strawberry.field
    def permissions(self, info: Info, active_only: Optional[bool] = None) -> list[Permission]:
        query = db_from(info).query(PermissionModel)
        if active_only:
            query = query.filter(PermissionModel.is_active.is_(True))
        return [permission_type(row) for row in query.order_by(PermissionModel.id).all()]

    @strawberry.field
    def role_permissions(self, info: Info, role_id: strawberry.ID) -> list[RolePermission]:
        db = db_from(info)
        if db.get(RoleModel, int(role_id)) is None:
            raise ValueError("El rol no existe")
        rows = db.query(RolePermissionModel).options(
            joinedload(RolePermissionModel.role), joinedload(RolePermissionModel.permission)
        ).filter(
            RolePermissionModel.role_id == int(role_id),
            RolePermissionModel.is_active.is_(True),
        ).order_by(RolePermissionModel.id).all()
        return [role_permission_type(row) for row in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_company(self, info: Info, input: CreateCompanyInput) -> Company:
        db = db_from(info)
        email = normalize_email(input.email) if input.email else None
        row = CompanyModel(
            name=required_text(input.name, "El nombre"), legal_name=input.legal_name,
            tax_id=input.tax_id, email=email, phone=input.phone,
        )
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            return company_type(row)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ya existe una empresa con ese identificador fiscal") from exc

    @strawberry.mutation
    def update_company(self, info: Info, input: UpdateCompanyInput) -> Company:
        db = db_from(info)
        row = db.get(CompanyModel, int(input.id))
        if row is None:
            raise ValueError("La empresa no existe")
        fields = ("name", "legal_name", "tax_id", "email", "phone", "is_active")
        for field in fields:
            value = getattr(input, field)
            if value is not strawberry.UNSET:
                if field == "name" and value is not None:
                    value = required_text(value, "El nombre")
                if field == "email" and value:
                    value = normalize_email(value)
                setattr(row, field, value)
        try:
            db.commit()
            db.refresh(row)
            return company_type(row)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("El identificador fiscal ya está registrado") from exc

    @strawberry.mutation
    def deactivate_company(self, info: Info, id: strawberry.ID) -> Company:
        db = db_from(info)
        row = db.get(CompanyModel, int(id))
        if row is None:
            raise ValueError("La empresa no existe")
        row.is_active = False
        db.commit()
        db.refresh(row)
        return company_type(row)

    @strawberry.mutation
    def create_company_admin(self, info: Info, input: CreateCompanyAdminInput) -> CompanyUser:
        return create_membership(info, input, True)

    @strawberry.mutation
    def create_company_user(
        self, info: Info, input: CreateCompanyUserInput, actor_company_user_id: strawberry.ID
    ) -> CompanyUser:
        require(info, actor_company_user_id, "company.users.write", input.company_id)
        return create_membership(info, input, False)

    @strawberry.mutation
    def deactivate_company_user(
        self, info: Info, id: strawberry.ID, actor_company_user_id: strawberry.ID
    ) -> CompanyUser:
        db = db_from(info)
        row = db.query(CompanyUserModel).options(
            joinedload(CompanyUserModel.company), joinedload(CompanyUserModel.user)
        ).filter(CompanyUserModel.id == int(id)).first()
        if row is None:
            raise ValueError("La relación empresa-usuario no existe")
        require(info, actor_company_user_id, "company.users.write", row.company_id)
        row.is_active = False
        db.commit()
        db.refresh(row)
        return membership_type(row)

    @strawberry.mutation
    def login(self, info: Info, input: LoginInput) -> AuthPayload:
        db = db_from(info)
        email = normalize_email(input.email)
        row = db.query(UserModel).filter(UserModel.email == email).first()
        if row is None or not row.is_active or not verify_password(input.password, row.password_hash):
            raise ValueError("Correo electrónico o contraseña incorrectos")
        return AuthPayload(
            token=create_access_token(row.id), token_type="Bearer",
            user=AuthUser(id=strawberry.ID(str(row.id)), name=row.name, email=row.email),
        )

    @strawberry.mutation
    def create_account(
        self, info: Info, input: CreateAccountInput, actor_company_user_id: strawberry.ID
    ) -> Account:
        db = db_from(info)
        require(info, actor_company_user_id, "accounts.write", input.company_id)
        company = active_company(db, input.company_id)
        if input.clabe and (len(input.clabe) != 18 or not input.clabe.isdigit()):
            raise ValueError("La CLABE debe contener exactamente 18 dígitos")
        if input.card_last_digits and (len(input.card_last_digits) != 4 or not input.card_last_digits.isdigit()):
            raise ValueError("Los últimos dígitos de tarjeta deben contener exactamente 4 números")
        row = AccountModel(
            company=company, account_type=input.account_type.value,
            name=required_text(input.name, "El nombre"), bank_name=input.bank_name,
            account_number=input.account_number, clabe=input.clabe,
            card_last_digits=input.card_last_digits, short_description=input.short_description,
            long_description=input.long_description,
        )
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            return account_to_graphql(row)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ya existe una cuenta con ese nombre en la empresa") from exc

    @strawberry.mutation
    def create_concept(
        self, info: Info, input: CreateConceptInput, actor_company_user_id: strawberry.ID
    ) -> Concept:
        db = db_from(info)
        require(info, actor_company_user_id, "concepts.write", input.company_id)
        company = active_company(db, input.company_id)
        row = ConceptModel(
            company=company, concept_type=input.concept_type.value,
            name=required_text(input.name, "El nombre"),
            short_description=input.short_description, long_description=input.long_description,
        )
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            return concept_to_graphql(row)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ya existe un concepto de ese tipo y nombre en la empresa") from exc

    @strawberry.mutation
    def assign_concept_to_account(
        self, info: Info, input: AssignConceptToAccountInput, actor_company_user_id: strawberry.ID
    ) -> AccountConcept:
        db = db_from(info)
        account = db.query(AccountModel).options(joinedload(AccountModel.company)).filter(
            AccountModel.id == int(input.account_id)
        ).first()
        concept = db.get(ConceptModel, int(input.concept_id))
        if account is None:
            raise ValueError("La cuenta no existe")
        require(info, actor_company_user_id, "concepts.write", account.company_id)
        if concept is None:
            raise ValueError("El concepto no existe")
        if not account.is_active or not concept.is_active:
            raise ValueError("La cuenta y el concepto deben estar activos")
        if account.company_id != concept.company_id:
            raise ValueError("La cuenta y el concepto deben pertenecer a la misma empresa")
        existing = db.query(AccountConceptModel).options(
            joinedload(AccountConceptModel.account).joinedload(AccountModel.company),
            joinedload(AccountConceptModel.concept),
        ).filter(
            AccountConceptModel.account_id == account.id,
            AccountConceptModel.concept_id == concept.id,
        ).first()
        if existing:
            if existing.is_active:
                raise ValueError("El concepto ya está asignado a la cuenta")
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return account_concept_to_graphql(existing)
        row = AccountConceptModel(account=account, concept=concept)
        db.add(row)
        db.commit()
        db.refresh(row)
        return account_concept_to_graphql(row)

    @strawberry.mutation
    def remove_concept_from_account(
        self, info: Info, account_id: strawberry.ID, concept_id: strawberry.ID,
        actor_company_user_id: strawberry.ID,
    ) -> bool:
        db = db_from(info)
        account = db.get(AccountModel, int(account_id))
        if account is None:
            raise ValueError("La cuenta no existe")
        require(info, actor_company_user_id, "concepts.write", account.company_id)
        row = db.query(AccountConceptModel).filter(
            AccountConceptModel.account_id == int(account_id),
            AccountConceptModel.concept_id == int(concept_id),
        ).first()
        if row is None:
            raise ValueError("La relación cuenta-concepto no existe")
        row.is_active = False
        db.commit()
        return True

    @strawberry.mutation
    def create_transaction(
        self, info: Info, input: CreateTransactionInput, actor_company_user_id: strawberry.ID
    ) -> Transaction:
        db = db_from(info)
        account = db.query(AccountModel).options(joinedload(AccountModel.company)).filter(
            AccountModel.id == int(input.account_id)
        ).first()
        if account is None:
            raise ValueError("La cuenta no existe")
        # El permiso se exige antes de validar o escribir nada.
        membership = require(info, actor_company_user_id, "transactions.write", account.company_id)
        user = membership.user
        concept = db.get(ConceptModel, int(input.concept_id))
        if input.amount <= 0:
            raise ValueError("El monto del movimiento debe ser mayor que cero")
        if concept is None:
            raise ValueError("El concepto no existe")
        if not account.is_active or not concept.is_active:
            raise ValueError("La cuenta y el concepto deben estar activos")
        if account.company_id != concept.company_id:
            raise ValueError("La cuenta y el concepto deben pertenecer a la misma empresa")
        allowed = db.query(AccountConceptModel).filter(
            AccountConceptModel.account_id == account.id,
            AccountConceptModel.concept_id == concept.id,
            AccountConceptModel.is_active.is_(True),
        ).first()
        if allowed is None:
            raise ValueError("El concepto no está permitido para la cuenta seleccionada")
        if input.transaction_type.value != concept.concept_type:
            raise ValueError("El tipo de movimiento no es compatible con el tipo de concepto")
        row = TransactionModel(
            account=account, concept=concept, transaction_type=input.transaction_type.value,
            amount=input.amount, transaction_date=input.transaction_date or datetime.now().astimezone(),
            captured_by_user=user, short_description=input.short_description,
            long_description=input.long_description,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return transaction_to_graphql(row)

    @strawberry.mutation
    def delete_transaction(
        self, info: Info, id: strawberry.ID, actor_company_user_id: strawberry.ID
    ) -> Transaction:
        db = db_from(info)
        row = db.query(TransactionModel).options(
            joinedload(TransactionModel.account).joinedload(AccountModel.company),
            joinedload(TransactionModel.concept), joinedload(TransactionModel.captured_by_user),
        ).filter(TransactionModel.id == int(id)).first()
        if row is None:
            raise ValueError("El movimiento no existe")
        require(info, actor_company_user_id, "transactions.write", row.account.company_id)
        row.is_active = False
        db.commit()
        db.refresh(row)
        return transaction_to_graphql(row)

    # ---------------- Roles ----------------

    @strawberry.mutation
    def create_role(self, info: Info, input: CreateRoleInput) -> Role:
        db = db_from(info)
        row = RoleModel(
            code=required_text(input.code, "El código").upper(),
            name=required_text(input.name, "El nombre"), description=input.description,
        )
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            return role_type(row)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ya existe un rol con ese código") from exc

    @strawberry.mutation
    def deactivate_role(self, info: Info, id: strawberry.ID) -> Role:
        db = db_from(info)
        row = db.get(RoleModel, int(id))
        if row is None:
            raise ValueError("El rol no existe")
        row.is_active = False
        db.commit()
        db.refresh(row)
        return role_type(row)

    # ---------------- Permisos ----------------

    @strawberry.mutation
    def create_permission(self, info: Info, input: CreatePermissionInput) -> Permission:
        db = db_from(info)
        row = PermissionModel(
            code=required_text(input.code, "El código").lower(),
            name=required_text(input.name, "El nombre"), description=input.description,
        )
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            return permission_type(row)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ya existe un permiso con ese código") from exc

    # ---------------- Permisos por rol ----------------

    @strawberry.mutation
    def assign_permission_to_role(
        self, info: Info, input: AssignPermissionToRoleInput, actor_company_user_id: strawberry.ID
    ) -> RolePermission:
        db = db_from(info)
        require(info, actor_company_user_id, "roles.write")
        role = db.get(RoleModel, int(input.role_id))
        permission = db.get(PermissionModel, int(input.permission_id))
        if role is None:
            raise ValueError("El rol no existe")
        if permission is None:
            raise ValueError("El permiso no existe")
        if not role.is_active or not permission.is_active:
            raise ValueError("El rol y el permiso deben estar activos")
        existing = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == role.id,
            RolePermissionModel.permission_id == permission.id,
        ).first()
        if existing:
            if existing.is_active:
                raise ValueError("El permiso ya está asignado al rol")
            existing.is_active = True
            row = existing
        else:
            row = RolePermissionModel(role=role, permission=permission)
            db.add(row)
        db.commit()
        db.refresh(row)
        return role_permission_type(row)

    @strawberry.mutation
    def remove_permission_from_role(
        self, info: Info, role_id: strawberry.ID, permission_id: strawberry.ID,
        actor_company_user_id: strawberry.ID,
    ) -> bool:
        db = db_from(info)
        require(info, actor_company_user_id, "roles.write")
        row = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == int(role_id),
            RolePermissionModel.permission_id == int(permission_id),
            RolePermissionModel.is_active.is_(True),
        ).first()
        if row is None:
            raise ValueError("El permiso no está asignado al rol")
        row.is_active = False
        db.commit()
        return True

    # ---------------- Rol de la membresía ----------------

    @strawberry.mutation
    def assign_role(
        self, info: Info, input: AssignRoleInput, actor_company_user_id: strawberry.ID
    ) -> CompanyUserRole:
        db = db_from(info)
        target = db.query(CompanyUserModel).options(
            joinedload(CompanyUserModel.company), joinedload(CompanyUserModel.user)
        ).filter(CompanyUserModel.id == int(input.company_user_id)).with_for_update().first()
        if target is None:
            raise ValueError("La membresía no existe")
        # Solo se administra el rol de membresías de la misma empresa del actor.
        require(info, actor_company_user_id, "roles.write", target.company_id)
        if not target.is_active:
            raise ValueError("La membresía está inactiva")
        role = db.get(RoleModel, int(input.role_id))
        if role is None:
            raise ValueError("El rol no existe")
        if not role.is_active:
            raise ValueError("El rol está inactivo")
        # isAdmin y el rol ADMINISTRADOR van de la mano.
        if target.is_admin and role.code != ADMIN_ROLE_CODE:
            raise ValueError("El administrador principal debe conservar el rol ADMINISTRADOR")
        if not target.is_admin and role.code == ADMIN_ROLE_CODE:
            raise ValueError("El rol ADMINISTRADOR es exclusivo del administrador principal")

        try:
            chosen = None
            for assignment in db.query(CompanyUserRoleModel).filter(
                CompanyUserRoleModel.company_user_id == target.id
            ).all():
                if assignment.role_id == role.id:
                    chosen = assignment
                elif assignment.is_active:
                    assignment.is_active = False  # el rol anterior queda inactivo
            if chosen is None:
                chosen = CompanyUserRoleModel(company_user_id=target.id, role_id=role.id)
                db.add(chosen)
            chosen.is_active = True
            db.commit()
            db.refresh(chosen)
            db.refresh(target)
            return company_user_role_type(chosen)
        except Exception:
            db.rollback()
            raise


schema = strawberry.Schema(query=Query, mutation=Mutation, scalar_overrides={datetime: Time})


async def graphql_context(request: Request, db: Session = Depends(get_db)):
    context = {"db": db, "current_user": None, "auth_error": None}
    authorization = request.headers.get("Authorization", "")
    if authorization:
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("El encabezado de autenticación debe usar Bearer")
            user_id = decode_access_token(token)
            user = db.get(UserModel, user_id)
            if user is None or not user.is_active:
                raise ValueError("El usuario autenticado no existe o está inactivo")
            context["current_user"] = user
        except ValueError as exc:
            context["auth_error"] = str(exc)
    return context


graphql_app = GraphQLRouter(schema, context_getter=graphql_context)
