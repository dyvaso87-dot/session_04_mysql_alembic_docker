# Actividad 5 — Gestión de roles y permisos (RBAC plano)

## Modelo

```text
Role N ──── role_permissions ──── N Permission
CompanyUser 1 ──── N company_user_roles N ──── 1 Role      (una pareja activa)
```

- `roles` y `permissions` son catálogos compartidos por todas las empresas. **No** hay columnas nuevas en `User`.
- `role_permissions` guarda la matriz. `company_user_roles` une la membresía (`CompanyUser`) con su rol.
- Nada se borra: `deactivateRole`, `removePermissionFromRole` y el cambio de rol solo ponen `is_active = false`.
- Códigos únicos: roles en MAYÚSCULAS (`CAPTURISTA`), permisos en minúsculas (`recurso.accion`).

## Dónde vive cada cosa

| Pieza | Archivo |
|---|---|
| Modelos SQLAlchemy (`Role`, `Permission`, `RolePermission`, `CompanyUserRole`) | `models/models.py` |
| Migración (no toca cuentas ni movimientos) | `alembic/versions/0004_roles_permisos.py` |
| Catálogos iniciales, matriz, `seed_access_control` y `exigir_permiso` | `access_control.py` |
| Tipos, queries y mutations GraphQL | `graphql_schema.py` |
| Seed al arrancar | `main.py` (`lifespan`) |
| Pruebas | `tests/test_activity5.py` |

## Cómo se decide un permiso

```text
actorCompanyUserId → membresía activa (y de la empresa del recurso)
                   → rol activo → permisos activos del rol → ¿está el código?
```

`exigir_permiso(db, company_user_id, codigo, company_id=None)` lanza `PermissionError` si falta algo, **antes** de escribir, así que un rechazo nunca deja una fila a medias (no hay `commit`). El parámetro `company_id` garantiza que los datos de una empresa no se mezclen con los de otra.

## Operaciones protegidas

| Operación | Permiso |
|---|---|
| `createCompanyUser`, `deactivateCompanyUser` | `company.users.write` |
| `companyUsers` | `company.users.read` |
| `createAccount` | `accounts.write` |
| `accounts` | `accounts.read` |
| `createConcept`, `assignConceptToAccount`, `removeConceptFromAccount` | `concepts.write` |
| `concepts`, `accountConcepts` | `concepts.read` |
| `createTransaction`, `deleteTransaction` | `transactions.write` |
| `transactions` | `transactions.read` |
| `assignRole`, `assignPermissionToRole`, `removePermissionFromRole` | `roles.write` |

Todas reciben `actorCompanyUserId`. Si además llega un token Bearer, debe pertenecer al mismo usuario de esa membresía; sin token basta el id (alcance de esta actividad; la siguiente tomará la identidad del token).

## Reglas extra (para no romper reglas anteriores)

- `createCompanyAdmin` sigue poniendo `isAdmin = true` **y** asigna el rol `ADMINISTRADOR` en la misma transacción.
- `assignRole` no permite cambiarle el rol al administrador principal ni dar `ADMINISTRADOR` a quien no lo es, para que `isAdmin` y el rol no se contradigan.
- Al arrancar, los administradores principales que existían antes de esta actividad y no tenían rol reciben `ADMINISTRADOR`.

## Pendientes conocidos (fuera del alcance del documento)

`createRole`, `createPermission`, `deactivateRole`, `createCompany`, `updateCompany` y `deactivateCompany` no piden actor, tal como lo define el documento; conviene protegerlas cuando el control de acceso tome la identidad del token.
