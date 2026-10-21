# Actividad 4 — Pruebas y evidencias GraphQL

## Preparación

```bash
docker compose up -d --build
docker compose run --rm api alembic upgrade head
```

En producción se debe definir `JWT_SECRET` con un valor largo y aleatorio; Docker Compose incluye únicamente un valor de desarrollo para facilitar las pruebas.

Abrir `http://localhost:8000/graphql`. Primero crear una empresa y su administrador con las operaciones de la Actividad 3.

## Autenticación

Ejecutar `login` y copiar el token. En la sección **HTTP HEADERS** de GraphiQL usar:

```json
{"Authorization": "Bearer TOKEN_OBTENIDO"}
```

## Crear y consultar cuentas

```graphql
mutation {
  createAccount(input: {
    companyId: "1", accountType: DEBIT, name: "Cuenta bancaria",
    bankName: "Banco Demo", accountNumber: "0012345678",
    clabe: "012345678901234567", cardLastDigits: "5678"
  }) { id companyId accountType name bankName isActive company { id name } }
}
```

Crear también cuentas `CASH` y `SAVINGS`, cambiando el nombre. Consultarlas con:

```graphql
query { accounts(companyId: "1", activeOnly: true) { id name accountType } }
```

## Crear y consultar conceptos

```graphql
mutation {
  createConcept(input: {
    companyId: "1", conceptType: INCOME, name: "Venta",
    shortDescription: "Ingreso por venta"
  }) { id companyId conceptType name isActive }
}
```

Crear cinco conceptos `INCOME` y cinco `EXPENSE`. Consultarlos con:

```graphql
query { concepts(companyId: "1", conceptType: INCOME, activeOnly: true) { id name } }
```

## Asociar conceptos

```graphql
mutation {
  assignConceptToAccount(input: { accountId: "1", conceptId: "1" }) {
    id accountId conceptId isActive account { name } concept { name conceptType }
  }
}
```

Crear al menos diez asociaciones y consultar:

```graphql
query { accountConcepts(accountId: "1") { id isActive concept { id name conceptType } } }
```

Para desactivar:

```graphql
mutation { removeConceptFromAccount(accountId: "1", conceptId: "1") }
```

## Registrar movimientos

Reactivar la asociación repitiendo `assignConceptToAccount` y ejecutar con el encabezado Bearer:

```graphql
mutation {
  createTransaction(input: {
    accountId: "1", conceptId: "1", transactionType: INCOME,
    amount: 1500.50, shortDescription: "Venta de contado"
  }) {
    id transactionType amount transactionDate capturedAt capturedBy
    account { id name } concept { id name } capturedByUser { id name email }
  }
}
```

Registrar al menos veinte movimientos alternando conceptos `INCOME` y `EXPENSE`. Consultar:

```graphql
query {
  transactions(accountId: "1", limit: 100, offset: 0) {
    id transactionType amount isActive concept { name } capturedByUser { email }
  }
}
```

Eliminar lógicamente un movimiento:

```graphql
mutation { deleteTransaction(id: "1") { id isActive updatedAt } }
```

## Casos de error que deben documentarse

- Repetir una cuenta con el mismo nombre y empresa.
- Repetir un concepto o una asociación cuenta–concepto.
- Enviar `amount: 0` o un monto negativo.
- Usar un concepto que no esté asignado a la cuenta.
- Enviar `EXPENSE` con un concepto `INCOME`.
- Omitir el encabezado `Authorization`.
- Usar una cuenta, concepto o usuario de otra empresa.

## Prueba automatizada y mínimos requeridos

```bash
python -m unittest discover -s tests -v
```

`test_activity4.py` genera y verifica automáticamente 3 cuentas, 5 conceptos de ingreso, 5 de egreso, 10 relaciones y 20 movimientos, además de los principales casos de error.
