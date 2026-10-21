from database.database import get_connection

# ==================================================
# ALUMNOS
# ==================================================


# CREATE
def crear_alumno(nombre):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        INSERT INTO alumnos (nombre)
        VALUES (%s)
        RETURNING id, nombre;
    """

    cursor.execute(sql, (nombre,))

    alumno = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "id": alumno[0],
        "nombre": alumno[1]
    }



# RETRIEVE - TODOS
def obtener_alumnos():
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        SELECT id, nombre
        FROM alumnos
        ORDER BY id;
    """

    cursor.execute(sql)

    resultados = cursor.fetchall()

    cursor.close()
    connection.close()

    alumnos = []

    for alumno in resultados:
        alumnos.append({
            "id": alumno[0],
            "nombre": alumno[1]
        })

    return alumnos

# RETRIEVE - UNO
def obtener_alumno(alumno_id):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        SELECT id, nombre
        FROM alumnos
        WHERE id = %s;
    """

    cursor.execute(sql, (alumno_id,))

    alumno = cursor.fetchone()

    cursor.close()
    connection.close()

    if alumno is None:
        return None

    return {
        "id": alumno[0],
        "nombre": alumno[1]
    }

# UPDATE
def actualizar_alumno(alumno_id, nombre):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        UPDATE alumnos
        SET nombre = %s
        WHERE id = %s
        RETURNING id, nombre;
    """

    cursor.execute(sql, (nombre, alumno_id))

    alumno = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    if alumno is None:
        return None

    return {
        "id": alumno[0],
        "nombre": alumno[1]
    }


# DELETE
def eliminar_alumno(alumno_id):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        DELETE FROM alumnos
        WHERE id = %s
        RETURNING id, nombre;
    """

    cursor.execute(sql, (alumno_id,))

    alumno = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    if alumno is None:
        return None

    return {
        "id": alumno[0],
        "nombre": alumno[1]
    }

# ==================================================
# MATERIAS
# ==================================================

# CREATE
def crear_materia(nombre):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        INSERT INTO materias (materia)
        VALUES (%s)
        RETURNING id, materia;
    """

    cursor.execute(sql, (nombre,))

    materia = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "id": materia[0],
        "nombre": materia[1]
    }



# RETRIEVE - TODOS
def obtener_materias():
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        SELECT id, materia
        FROM materias
        ORDER BY id;
    """

    cursor.execute(sql)

    resultados = cursor.fetchall()

    cursor.close()
    connection.close()

    materias = []

    for materia in resultados:
        materias.append({
            "id": materia[0],
            "nombre": materia[1]
        })

    return materias

# RETRIEVE - UNO
def obtener_materia(materia_id):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        SELECT id, materia
        FROM materias
        WHERE id = %s;
    """

    cursor.execute(sql, (materia_id,))

    materia = cursor.fetchone()

    cursor.close()
    connection.close()

    if materia is None:
        return None

    return {
        "id": materia[0],
        "nombre": materia[1]
    }

# UPDATE
def actualizar_materia(materia_id, nombre):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        UPDATE materias
        SET materia = %s
        WHERE id = %s
        RETURNING id, materia;
    """

    cursor.execute(sql, (nombre, materia_id))

    materia = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    if materia is None:
        return None

    return {
        "id": materia[0],
        "nombre": materia[1]
    }


# DELETE
def eliminar_materia(materia_id):
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        DELETE FROM materias
        WHERE id = %s
        RETURNING id, materia;
    """

    cursor.execute(sql, (materia_id,))

    materia = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    if materia is None:
        return None

    return {
        "id": materia[0],
        "nombre": materia[1]
    }


# ==================================================
# PRODUCTOS
# ==================================================

from models.models import Producto


def crear_producto(db, producto):
    nuevo_producto = Producto(**producto.model_dump())

    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)

    return nuevo_producto


def obtener_productos(db):
    return db.query(Producto).order_by(Producto.id).all()


def obtener_producto(db, producto_id):
    return (
        db.query(Producto)
        .filter(Producto.id == producto_id)
        .first()
    )


def obtener_productos_disponibles(db):
    return (
        db.query(Producto)
        .filter(Producto.stock > 0)
        .order_by(Producto.id)
        .all()
    )


def actualizar_producto(db, producto_id, producto):
    producto_db = obtener_producto(db, producto_id)

    if producto_db is None:
        return None

    for campo, valor in producto.model_dump().items():
        setattr(producto_db, campo, valor)

    db.commit()
    db.refresh(producto_db)

    return producto_db


def eliminar_producto(db, producto_id):
    producto_db = obtener_producto(db, producto_id)

    if producto_db is None:
        return None

    producto_eliminado = {
        "id": producto_db.id,
        "nombre": producto_db.nombre,
        "descripcion": producto_db.descripcion,
        "precio": producto_db.precio,
        "stock": producto_db.stock,
    }

    db.delete(producto_db)
    db.commit()

    return producto_eliminado
