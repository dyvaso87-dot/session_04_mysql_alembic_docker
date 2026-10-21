# Endpoints de materias

## Crear una materia

```http
POST /materias
```

```json
{
  "nombre": "Introduccion al Backend"
}
```

## Consultar todas las materias

```http
GET /materias
```

## Consultar una materia por id

```http
GET /materias/{materia_id}
```

## Actualizar una materia

```http
PUT /materias/{materia_id}
```

```json
{
  "nombre": "Base de Datos"
}
```

## Eliminar una materia

```http
DELETE /materias/{materia_id}
```
