import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from access_control import seed_access_control
from database.database import SessionLocal
from routers.routes import router
from graphql_schema import graphql_app

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Datos iniciales de la Actividad 5: 4 roles, 10 permisos y la matriz.
    # Es idempotente: si ya existen, no se duplican.
    try:
        with SessionLocal() as db:
            seed_access_control(db)
    except SQLAlchemyError as exc:
        logger.warning(
            "No se pudieron cargar roles y permisos iniciales. "
            "¿Ya ejecutaste 'alembic upgrade head'? Detalle: %s", exc
        )
    yield


app = FastAPI(
    title="Sistema financiero - Empresas y Usuarios",
    version="1.0.0",
    lifespan=lifespan,
)


# ==================================================
# ROUTES
# ==================================================

app.include_router(router)
app.include_router(graphql_app, prefix="/graphql")
