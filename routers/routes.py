from fastapi import APIRouter, HTTPException

from models.models import (
    AlumnoCreate,
    AlumnoUpdate,
    MateriaCreate,
    MateriaUpdate
)

from repositories.crud import (
    crear_alumno,
    obtener_alumnos,
    obtener_alumno,
    actualizar_alumno,
    eliminar_alumno,
    crear_materia,
    obtener_materias,
    obtener_materia,
    actualizar_materia,
    eliminar_materia,
)


router = APIRouter()


# ==================================================
# HOLA MUNDO
# ==================================================

@router.get("/")
def hola_mundo():
    return {
        "mensaje": "Hola Mundo"
    }


# ==================================================
# SALUDO
# ==================================================

@router.get("/saludo/{nombre}")
def saludo(nombre: str):
    return {
        "nombre": nombre,
        "mensaje": f"Hola {nombre}, bienvenido a FastAPI"
    }


# ==================================================
# CRUD ALUMNOS
# ==================================================

# CREATE
@router.post("/alumnos")
def agregar_alumno(alumno: AlumnoCreate):

    nuevo_alumno = crear_alumno(alumno.nombre)

    return {
        "mensaje": "Alumno creado correctamente",
        "alumno": nuevo_alumno
    }


# RETRIEVE - TODOS
@router.get("/alumnos")
def listar_alumnos():

    return obtener_alumnos()


# RETRIEVE - UNO
@router.get("/alumnos/{alumno_id}")
def consultar_alumno(alumno_id: int):

    alumno = obtener_alumno(alumno_id)

    if alumno is None:
        raise HTTPException(
            status_code=404,
            detail="Alumno no encontrado"
        )

    return alumno


# UPDATE
@router.put("/alumnos/{alumno_id}")
def modificar_alumno(
    alumno_id: int,
    alumno: AlumnoUpdate
):

    alumno_actualizado = actualizar_alumno(
        alumno_id,
        alumno.nombre
    )

    if alumno_actualizado is None:
        raise HTTPException(
            status_code=404,
            detail="Alumno no encontrado"
        )

    return {
        "mensaje": "Alumno actualizado correctamente",
        "alumno": alumno_actualizado
    }


# DELETE
@router.delete("/alumnos/{alumno_id}")
def borrar_alumno(alumno_id: int):

    alumno_eliminado = eliminar_alumno(alumno_id)

    if alumno_eliminado is None:
        raise HTTPException(
            status_code=404,
            detail="Alumno no encontrado"
        )

    return {
        "mensaje": "Alumno eliminado correctamente",
        "alumno": alumno_eliminado
    }

# ==================================================
# CRUD MATERIAS
# ==================================================

# CREATE
@router.post("/materias")
def agregar_materias(materia: MateriaCreate):

    nuevo_materia = crear_materia(materia.nombre)

    return {
        "mensaje": "Materia creado correctamente",
        "materia": nuevo_materia
    }


# RETRIEVE - TODOS
@router.get("/materias")
def listar_materias():

    return obtener_materias()


# RETRIEVE - UNO
@router.get("/materias/{materia_id}")
def consultar_materia(materia_id: int):

    materia = obtener_materia(materia_id)

    if materia is None:
        raise HTTPException(
            status_code=404,
            detail="Materia no encontrado"
        )

    return materia


# UPDATE
@router.put("/materias/{materia_id}")
def modificar_materia(
    materia_id: int,
    materia: MateriaUpdate
):

    materia_actualizado = actualizar_materia(
        materia_id,
        materia.nombre
    )

    if materia_actualizado is None:
        raise HTTPException(
            status_code=404,
            detail="Materia no encontrado"
        )

    return {
        "mensaje": "Materia actualizado correctamente",
        "Materia": materia_actualizado
    }


# DELETE
@router.delete("/materias/{materia_id}")
def borrar_materia(materia_id: int):

    materia_eliminado = eliminar_materia(materia_id)

    if materia_eliminado is None:
        raise HTTPException(
            status_code=404,
            detail="Materia no encontrado"
        )

    return {
        "mensaje": "Materia eliminado correctamente",
        "materia": materia_eliminado
    }


# ==================================================
# CRUD PRODUCTOS
# ==================================================

from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session

from database.database import get_db
from models.models import ProductoCreate, ProductoResponse, ProductoUpdate
from repositories.crud import (
    actualizar_producto,
    crear_producto,
    eliminar_producto,
    obtener_producto,
    obtener_productos,
    obtener_productos_disponibles,
)


# CREATE
@router.post("/productos", response_model=ProductoResponse)
def agregar_producto(
    producto: ProductoCreate,
    db: Session = Depends(get_db),
):
    return crear_producto(db, producto)


# RETRIEVE - TODOS
@router.get("/productos", response_model=List[ProductoResponse])
def listar_productos(db: Session = Depends(get_db)):
    return obtener_productos(db)


# RETO ADICIONAL - DISPONIBLES
@router.get("/productos/disponibles", response_model=List[ProductoResponse])
def listar_productos_disponibles(db: Session = Depends(get_db)):
    return obtener_productos_disponibles(db)


# RETRIEVE - UNO
@router.get("/productos/{producto_id}", response_model=ProductoResponse)
def consultar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto = obtener_producto(db, producto_id)

    if producto is None:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    return producto


# UPDATE
@router.put("/productos/{producto_id}", response_model=ProductoResponse)
def modificar_producto(
    producto_id: int,
    producto: ProductoUpdate,
    db: Session = Depends(get_db),
):
    producto_actualizado = actualizar_producto(
        db,
        producto_id,
        producto,
    )

    if producto_actualizado is None:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    return producto_actualizado


# DELETE
@router.delete("/productos/{producto_id}")
def borrar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto_eliminado = eliminar_producto(db, producto_id)

    if producto_eliminado is None:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    return {
        "mensaje": "Producto eliminado correctamente",
        "producto": producto_eliminado,
    }
