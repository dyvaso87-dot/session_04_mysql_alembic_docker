# Actividad 4 — Análisis y reglas de negocio

## Modelo

```text
Company 1 ── N Account 1 ── N AccountConcept N ── 1 Concept N ── 1 Company
                         Account 1 ── N Transaction N ── 1 Concept
                                              N ── 1 User (capturedBy)
```

- `Account` representa una cuenta financiera perteneciente a una empresa.
- `Concept` clasifica ingresos o egresos y pertenece a una empresa.
- `AccountConcept` define qué conceptos pueden utilizarse en cada cuenta.
- `Transaction` registra el movimiento, su responsable y las referencias que permiten auditarlo.

## Reglas implementadas

1. Los nombres de cuentas son únicos dentro de cada empresa.
2. La combinación tipo–nombre de un concepto es única dentro de cada empresa.
3. Una asociación cuenta–concepto no puede duplicarse.
4. Una cuenta solo acepta conceptos de su propia empresa.
5. Cuenta, concepto, asociación, empresa y membresía del usuario deben estar activos.
6. Todo monto es positivo; `INCOME` suma y `EXPENSE` resta.
7. El tipo del movimiento debe coincidir con el tipo del concepto.
8. Solo un usuario autenticado y asociado a la empresa puede registrar movimientos.
9. Cada movimiento conserva `capturedBy` y `capturedAt` para auditoría.
10. La eliminación de asociaciones y movimientos es lógica mediante `isActive`.
11. La CLABE, cuando existe, contiene 18 dígitos; los últimos dígitos de tarjeta contienen 4.
12. Las consultas de movimientos autenticadas solo exponen empresas asociadas al usuario.

## Balance

```text
Balance = SUM(INCOME) - SUM(EXPENSE)
```

Los egresos también se almacenan como cantidades positivas; el signo se determina exclusivamente por `transactionType`.

## Participación del equipo

- **Leonardo Balmes Solís:** integración del proyecto y documentación del modelo financiero y sus reglas de negocio para cuentas, conceptos y movimientos.
- **Marcelo Medina Canto:** gestión de cuentas y conceptos del día 1, incluidas las relaciones `AccountConcept` y la revisión de las reglas que evitan duplicados y asociaciones entre empresas distintas. Su sección se relaciona con los modelos y operaciones GraphQL de cuentas y conceptos, así como con los casos correspondientes en `tests/test_activity4.py`.
- **Vazques Soriano Dylan:** validación de los movimientos financieros del día 2: ingresos y egresos, montos positivos, concepto permitido por cuenta, compatibilidad de tipos, autenticación y registro del usuario que capturó cada movimiento. Su sección se relaciona con los casos descritos en `docs/actividad4_pruebas.md` y con `tests/test_activity4.py`.
