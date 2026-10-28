# LIOS — Modo investigación

Backend y prototipo del experimento factorial 2×2 (diez rondas de inversión simulada). Al clonarlo y seguir estos pasos queda una base SQLite local y la aplicación en el navegador.

## Qué necesitas

- Python 3.12
- Git

## Puesta en marcha

Abre una terminal en la carpeta del repositorio (donde están `requirements.txt` y `app/`).

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Deja esa terminal abierta. Entra en [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

El servidor debe arrancar desde esta carpeta y con un solo proceso. Con la configuración de arriba, la base queda en `lios.db` y la asignación de condiciones no se desbalancea.

## Si usas PostgreSQL

El driver ya entra con `pip install -r requirements.txt`. Quien use SQLite no tiene que configurarlo. Quien use PostgreSQL necesita el servidor en marcha y una base vacía, por ejemplo `lios`.

En `.env`, sustituye la línea de la base por la tuya:

```text
DATABASE_URL=postgresql+psycopg://USUARIO:CONTRASEÑA@localhost:5432/lios
```

Reinicia Uvicorn. Al arrancar se crean `participants` y `round_logs`. El recorrido y la exportación CSV son los mismos. Los datos quedan en Postgres, no en `lios.db`. Sigue siendo un solo proceso de Uvicorn.

## Cómo probar el recorrido

1. En el dashboard, pulsa **Nueva inversión**.
2. Acepta la participación y completa el perfil: 18 años o más, país y al menos una inversión personal.
3. Al continuar, el servidor crea la sesión y asigna la condición (C1, C2, C3 o C4).
4. Recorre las 10 propuestas. En cada una elige A o B y confirma.
5. Responde la intención de uso (IU1–IU3) y los dos controles.
6. En el cierre debe aparecer un identificador largo (UUID), no un código `DEMO-`.

Con SQLite, la primera vez se crea `lios.db` en esta carpeta. Puedes repetir el recorrido: cada perfil nuevo es otra sesión.

## Exportar los datos

Con el servidor en marcha:

[http://127.0.0.1:8000/api/v1/experiment/admin/export-csv?token=change-me](http://127.0.0.1:8000/api/v1/experiment/admin/export-csv?token=change-me)

`change-me` es el token de `.env.example`. Si lo cambias en tu `.env`, usa ese valor y reinicia el servidor. El archivo trae una fila por ronda. Para el análisis en R, quédate con las sesiones completadas (`completed == TRUE`).

## Archivos que se quedan en tu máquina

`.env` y `lios.db` no se suben al repositorio. El primero guarda el token y, si aplica, la contraseña de Postgres. `lios.db` solo existe cuando se usa SQLite.
