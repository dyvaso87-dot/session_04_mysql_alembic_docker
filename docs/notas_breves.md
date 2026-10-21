# FastAPI + Docker + Docker Compose

1. Crear `requirements.txt`

```text
fastapi
uvicorn[standard]
```

2. Crear `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

3. Crear `.dockerignore`

```text
venv
.venv
__pycache__
*.pyc
.git
.env
```

4. Crear `.env`

```env
APP_PORT=8000
```

5. Crear `compose.yaml`

```yaml
services:

  api:

    build:
      context: .
      dockerfile: Dockerfile

    container_name: fastapi-api

    ports:
      - "${APP_PORT}:8000"

    restart: unless-stopped
```

6. La estructura debe quedar así

```text
proyecto/
├── main.py
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── .env
└── .dockerignore
```

7. Validar Docker

```powershell
docker --version
docker compose version
```

8. Construir y levantar

```powershell
docker compose up -d --build
```

9. Verificar que esté corriendo

```powershell
docker compose ps
```

10. Ver logs

```powershell
docker compose logs -f
```

Salir de los logs:

```text
CTRL + C
```

11. Abrir FastAPI

```text
http://localhost:8000
```

12. Abrir Swagger

```text
http://localhost:8000/docs
```

13. Detener el proyecto

```powershell
docker compose down
```

14. Volver a levantar

```powershell
docker compose up -d
```

15. Si cambia código, Dockerfile o dependencias

```powershell
docker compose up -d --build
```

16. Cambiar el puerto

Editar `.env`:

```env
APP_PORT=9000
```

Reiniciar:

```powershell
docker compose down
docker compose up -d
```

Ahora abrir:

```text
http://localhost:9000/docs
```

17. Comando principal de la clase

```powershell
docker compose up -d --build
```

18. Idea final

```text
requirements.txt = dependencias de Python
Dockerfile        = cómo construir la imagen
compose.yaml      = cómo ejecutar el contenedor
.env              = configuración del puerto
```
