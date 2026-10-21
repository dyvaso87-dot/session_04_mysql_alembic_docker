# Actividad 5 — Pruebas y capturas

## Preparación

```bash
docker compose up -d --build
docker compose run --rm api alembic upgrade head
docker compose restart api        # el seed corre al arrancar (ya con las tablas creadas)
```

Abrir `http://localhost:8000/graphql`. Para probar sin Docker: `alembic upgrade head` y `python -m uvicorn main:app`.

Prueba automática: `python -m unittest discover -s tests -v`

## Datos de apoyo (ejecutar una vez, en este orden)

```graphql
mutation { createCompany(input: {name: "Empresa A"}) { id } }
```
```graphql
mutation { createCompanyAdmin(input: {companyId: "1", name: "Admin", email: "admin@a.com", password: "ClaveSegura123"}) { id isAdmin role { code } } }
```
El `id` devuelto es la membresía del administrador (**ADMIN = 1**). Con ella se crean los demás usuarios:

```graphql
mutation { createCompanyUser(input: {companyId: "1", name: "Cap", email: "cap@a.com", password: "ClaveSegura123"}, actorCompanyUserId: "1") { id } }
mutation { createCompanyUser(input: {companyId: "1", name: "Con", email: "con@a.com", password: "ClaveSegura123"}, actorCompanyUserId: "1") { id } }
mutation { createCompanyUser(input: {companyId: "1", name: "Ctd", email: "ctd@a.com", password: "ClaveSegura123"}, actorCompanyUserId: "1") { id } }
```
Supón CAP = 2, CON = 3, CTD = 4. Los ids de rol salen de `roles` (ADMINISTRADOR 1, CONTADOR 2, CAPTURISTA 3, CONSULTA 4):

```graphql
mutation { assignRole(input: {companyUserId: "2", roleId: "3"}, actorCompanyUserId: "1") { role { code } isActive } }
mutation { assignRole(input: {companyUserId: "3", roleId: "4"}, actorCompanyUserId: "1") { role { code } isActive } }
mutation { assignRole(input: {companyUserId: "4", roleId: "2"}, actorCompanyUserId: "1") { role { code } isActive } }
```
Preparar una cuenta y un concepto para los movimientos (con el contador, 4):
```graphql
mutation { createAccount(input: {companyId: "1", accountType: CASH, name: "Caja"}, actorCompanyUserId: "4") { id } }
mutation { createConcept(input: {companyId: "1", conceptType: INCOME, name: "Venta"}, actorCompanyUserId: "4") { id } }
mutation { assignConceptToAccount(input: {accountId: "1", conceptId: "1"}, actorCompanyUserId: "4") { id } }
```

## Capturas y la frase de cada una

| # | Operación | Resultado esperado | Frase (qué regla demuestra) |
|---|---|---|---|
| 1 | `{ roles { code } }` | 4 códigos | Los roles son un catálogo con los cuatro puestos iniciales. |
| 2 | `{ permissions { code } }` | 10 códigos | El catálogo de permisos sale de las operaciones que ya existen. |
| 3 | `{ rolePermissions(roleId: "3") { permission { code } } }` | incluye `transactions.write`, no `accounts.write` | El capturista registra movimientos pero no crea cuentas. |
| 4 | `{ rolePermissions(roleId: "4") { permission { code } } }` | ningún `.write` | El rol Consulta solo lee. |
| 5 | `createTransaction` con `actorCompanyUserId: "2"` (capturista) | se guarda | Un rol con `transactions.write` sigue el camino normal. |
| 6 | `createTransaction` con `actorCompanyUserId: "3"` (consulta) | `errors`: "no tiene el permiso transactions.write" + `SELECT * FROM transactions` sin fila nueva | Si falta el permiso, no se escribe nada (no hay commit). |
| 7 | `createAccount` con actor `4` (contador) | se crea | El contador tiene `accounts.write`. |
| 8 | `createAccount` con actor `2` (capturista) | `errors`: "accounts.write" | El capturista no puede crear cuentas. |
| 9 | `assignRole` capturista(2) → contador, luego `createAccount` con actor `2` | cambia el rol y ahora sí crea | Cambiar el rol cambia lo que puede hacer la persona, sin tocar permisos sueltos. |
| 10 | Segundo `createCompanyAdmin` en la empresa 1 | error "ya tiene un administrador principal" | `isAdmin` sigue impidiendo un segundo administrador principal. |
| 11 | Reiniciar (`docker compose restart api`) y `SELECT COUNT(*) FROM roles;` | 4 | El seed solo inserta cuando la tabla está vacía. |

Consulta para la captura 9 (antes y después):
```graphql
mutation { assignRole(input: {companyUserId: "2", roleId: "2"}, actorCompanyUserId: "1") { role { code } isActive } }
```

## SQL para comparar con la matriz

```sql
SELECT id, code, name, is_active FROM roles;
SELECT id, code, is_active FROM permissions;
SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.id, p.id;
SELECT COUNT(*) FROM transactions;   -- antes y después del movimiento rechazado
```
Esperado: ADMINISTRADOR 10, CONTADOR 8, CAPTURISTA 4, CONSULTA 4 (26 filas).
