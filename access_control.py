"""Control de acceso basado en roles (RBAC plano).

Contiene:
  - Los catálogos iniciales (4 roles, 10 permisos) y la matriz rol -> permisos
    exactamente como la define el documento de la actividad.
  - seed_access_control(): inserta lo anterior al arrancar, sin duplicar.
  - exigir_permiso(): la regla que consultan los resolvers antes de escribir.
"""

from sqlalchemy.orm import Session

from models.models import CompanyUser as CompanyUserModel
from models.models import CompanyUserRole as CompanyUserRoleModel
from models.models import Permission as PermissionModel
from models.models import Role as RoleModel
from models.models import RolePermission as RolePermissionModel


ADMIN_ROLE_CODE = "ADMINISTRADOR"

# (código, nombre, descripción)
INITIAL_ROLES = [
    ("ADMINISTRADOR", "Administrador", "Administrador principal de la empresa"),
    ("CONTADOR", "Contador", "Arma cuentas y conceptos y registra movimientos"),
    ("CAPTURISTA", "Capturista", "Registra ingresos y egresos"),
    ("CONSULTA", "Consulta", "Solo lectura"),
]

INITIAL_PERMISSIONS = [
    ("company.users.read", "Ver usuarios de la empresa", "Ver las membresías de la empresa"),
    ("company.users.write", "Administrar usuarios", "Crear usuarios y desactivar membresías"),
    ("accounts.read", "Consultar cuentas", "Consultar cuentas"),
    ("accounts.write", "Crear cuentas", "Crear cuentas"),
    ("concepts.read", "Consultar conceptos", "Consultar conceptos"),
    ("concepts.write", "Crear conceptos", "Crear conceptos y asignarlos a una cuenta"),
    ("transactions.read", "Consultar movimientos", "Consultar movimientos"),
    ("transactions.write", "Registrar movimientos", "Registrar un ingreso o un egreso"),
    ("roles.read", "Ver roles", "Ver roles y la matriz de permisos"),
    ("roles.write", "Administrar roles", "Asignar o quitar permisos de un rol y asignar un rol a una membresía"),
]

# Matriz del documento (filas = permisos, columnas = roles), leída por rol.
ROLE_PERMISSION_MATRIX = {
    "ADMINISTRADOR": [code for code, _, _ in INITIAL_PERMISSIONS],
    "CONTADOR": [
        "company.users.read",
        "accounts.read", "accounts.write",
        "concepts.read", "concepts.write",
        "transactions.read", "transactions.write",
        "roles.read",
    ],
    "CAPTURISTA": [
        "accounts.read",
        "concepts.read",
        "transactions.read", "transactions.write",
    ],
    "CONSULTA": [
        "company.users.read",
        "accounts.read",
        "concepts.read",
        "transactions.read",
    ],
}


def seed_access_control(db: Session) -> None:
    """Carga los datos iniciales. Es idempotente: un reinicio no duplica nada."""
    try:
        # 1) Roles y permisos: solo si la tabla está vacía.
        if db.query(RoleModel).count() == 0:
            for code, name, description in INITIAL_ROLES:
                db.add(RoleModel(code=code, name=name, description=description))
        if db.query(PermissionModel).count() == 0:
            for code, name, description in INITIAL_PERMISSIONS:
                db.add(PermissionModel(code=code, name=name, description=description))
        db.flush()

        # 2) Matriz: solo para los roles que todavía no tienen ningún permiso.
        roles = {r.code: r for r in db.query(RoleModel).all()}
        permissions = {p.code: p for p in db.query(PermissionModel).all()}
        for role_code, permission_codes in ROLE_PERMISSION_MATRIX.items():
            role = roles.get(role_code)
            if role is None:
                continue
            has_permissions = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == role.id
            ).count()
            if has_permissions:
                continue
            for permission_code in permission_codes:
                permission = permissions.get(permission_code)
                if permission is not None:
                    db.add(RolePermissionModel(role_id=role.id, permission_id=permission.id))
        db.flush()

        # 3) Administradores principales que ya existían antes de esta actividad
        #    y todavía no tienen rol: reciben ADMINISTRADOR.
        admin_role = roles.get(ADMIN_ROLE_CODE)
        if admin_role is not None:
            with_role = db.query(CompanyUserRoleModel.company_user_id).filter(
                CompanyUserRoleModel.is_active.is_(True)
            )
            orphans = db.query(CompanyUserModel).filter(
                CompanyUserModel.is_admin.is_(True),
                CompanyUserModel.is_active.is_(True),
                ~CompanyUserModel.id.in_(with_role),
            ).all()
            for membership in orphans:
                db.add(CompanyUserRoleModel(company_user_id=membership.id, role_id=admin_role.id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def exigir_permiso(
    db: Session, company_user_id: int, codigo: str, company_id: int | None = None
) -> CompanyUserModel:
    """Lanza PermissionError si la membresía no puede ejecutar `codigo`.

    Cadena: membresía -> rol activo -> permisos activos del rol -> ¿está `codigo`?
    Si se pasa `company_id`, además la membresía debe pertenecer a esa empresa
    (los datos de una empresa no se mezclan con los de otra).
    Devuelve la membresía para que el resolver sepa quién actúa.
    """
    membership = db.get(CompanyUserModel, int(company_user_id))
    if membership is None or not membership.is_active:
        raise PermissionError("La membresía no existe o está inactiva")
    if company_id is not None and membership.company_id != int(company_id):
        raise PermissionError("La membresía no pertenece a la empresa del recurso")

    asignacion = (
        db.query(CompanyUserRoleModel)
        .join(RoleModel, RoleModel.id == CompanyUserRoleModel.role_id)
        .filter(
            CompanyUserRoleModel.company_user_id == membership.id,
            CompanyUserRoleModel.is_active.is_(True),
            RoleModel.is_active.is_(True),
        )
        .first()
    )
    if asignacion is None:
        raise PermissionError("La membresía no tiene un rol activo")

    permitido = (
        db.query(RolePermissionModel)
        .join(PermissionModel, PermissionModel.id == RolePermissionModel.permission_id)
        .filter(
            RolePermissionModel.role_id == asignacion.role_id,
            RolePermissionModel.is_active.is_(True),
            PermissionModel.code == codigo,
            PermissionModel.is_active.is_(True),
        )
        .first()
    )
    if permitido is None:
        raise PermissionError(f"El rol no tiene el permiso {codigo}")
    return membership
