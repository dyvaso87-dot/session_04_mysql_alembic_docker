# Actividad 3 — Guía de ejecución y evidencias GraphQL

## Preparación

```bash
docker compose up -d --build
docker compose run --rm api alembic upgrade head
```

Abrir `http://localhost:8000/graphql` y ejecutar cada operación. Las respuestas obtenidas pueden capturarse como evidencias.

## Día 1: empresas

```graphql
mutation {
  createCompany(input: {
    name: "Finanzas del Sureste"
    legalName: "Finanzas del Sureste, S.A. de C.V."
    taxId: "FDS260919ABC"
    email: "contacto@example.com"
    phone: "+52 999 123 4567"
  }) { id name legalName taxId email phone isActive createdAt updatedAt }
}
```

```graphql
query { companies(activeOnly: true) { id name isActive } }
query { company(id: "1") { id name legalName taxId } }
```

```graphql
mutation {
  updateCompany(input: { id: "1", phone: "+52 999 765 4321" }) {
    id name phone updatedAt
  }
}
```

```graphql
mutation { deactivateCompany(id: "1") { id name isActive } }
mutation { updateCompany(input: { id: "1", isActive: true }) { id isActive } }
```

La segunda operación reactiva la empresa para continuar con el día 2.

## Día 2: usuarios y autenticación

### 1. Creación correcta del administrador

```graphql
mutation {
  createCompanyAdmin(input: {
    companyId: "1", name: "Ana Admin",
    email: "ana@example.com", password: "ClaveSegura123"
  }) { id companyId userId isAdmin isActive user { id name email } company { id name } }
}
```

### 2. Creación correcta de usuario

```graphql
mutation {
  createCompanyUser(input: {
    companyId: "1", name: "Uriel Usuario",
    email: "uriel@example.com", password: "OtraClave123"
  }) { id isAdmin isActive joinedAt user { id name email } }
}
```

```graphql
query {
  companyUsers(companyId: "1") {
    id isAdmin isActive user { id name email } company { id name }
  }
}
```

### 3. Correo duplicado

Repetir `createCompanyUser` con `email: "uriel@example.com"`. Debe devolver un error.

### 4. Segundo administrador

Repetir `createCompanyAdmin` para `companyId: "1"` con otro correo. Debe devolver un error.

### 5. Empresa inexistente

Ejecutar `createCompanyUser` con `companyId: "99999"`. Debe devolver un error.

### 6. Autenticación correcta e incorrecta

```graphql
mutation {
  login(input: { email: "ana@example.com", password: "ClaveSegura123" }) {
    token tokenType user { id name email }
  }
}
```

Repetir con otra contraseña. La respuesta debe contener `Correo electrónico o contraseña incorrectos` y nunca revelar cuál dato falló.

## Comprobación en MySQL

```bash
docker exec -it fastapi-mysql mysql -u actividad3 -pactividad3 actividad3
```

```sql
SHOW TABLES;
SELECT id, name, is_active FROM companies;
SELECT id, name, email, password_hash, is_active FROM users;
SELECT id, company_id, user_id, is_admin, is_active FROM company_users;
```

`password_hash` debe comenzar con `pbkdf2_sha256$`; la contraseña original no debe aparecer.
