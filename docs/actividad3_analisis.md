# Actividad 3 — Análisis del dominio

## Actores

- Administrador del sistema: supervisa las empresas registradas.
- Administrador principal de empresa: administra los usuarios de su empresa.
- Usuario de empresa: utiliza las funciones financieras autorizadas.

## Entidades y atributos

- **Company**: id, name, legalName, taxId, email, phone, isActive, createdAt y updatedAt.
- **User**: id, name, email, passwordHash, emailVerified, isActive, createdAt y updatedAt.
- **CompanyUser**: id, companyId, userId, isAdmin, isActive y joinedAt.

`passwordHash` nunca se expone en GraphQL.

## Relaciones y cardinalidades

```text
Company 1 ─── N CompanyUser N ─── 1 User
```

- Una empresa puede tener muchas membresías de usuario.
- Un usuario puede relacionarse posteriormente con varias empresas gracias a la entidad intermedia.
- Una membresía pertenece exactamente a una empresa y a un usuario.
- Cada empresa puede tener como máximo un administrador principal activo.

## Reglas de negocio

1. El nombre de empresa y el nombre de usuario son obligatorios y no pueden estar vacíos.
2. `taxId`, cuando se proporciona, debe ser único.
3. Los correos se validan, normalizan a minúsculas y no pueden repetirse.
4. Las contraseñas deben tener al menos ocho caracteres y se almacenan con PBKDF2-SHA256, salt aleatorio y 600 000 iteraciones.
5. Solo se puede registrar un administrador principal activo por empresa.
6. No se pueden registrar usuarios en empresas inexistentes o inactivas.
7. Empresa y membresía se eliminan lógicamente mediante `isActive`; se conserva el historial.
8. La autenticación requiere un usuario activo y credenciales válidas; el token expira en una hora.
9. La consulta de usuarios se limita por `companyId` para mantener separados los datos empresariales.

## Decisiones de diseño

El bloqueo de la fila de la empresa durante la creación del administrador reduce condiciones de carrera. Las restricciones únicas de base de datos complementan las validaciones de la aplicación. La API conserva los endpoints REST anteriores, pero la actividad nueva se publica en `/graphql`.
