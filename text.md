/e-learning-platform
│
├── app/
│   ├── __init__.py
│   ├── main.py         # El archivo principal de FastAPI
│   ├── models.py       # Aquí defines tus modelos SQL (con SQLModel)
│   ├── schemas.py      # Esquemas de Pydantic para validación
│   └── crud.py         # Operaciones CRUD (crear, leer, actualizar, eliminar)
│
└── venv/               # Tu entorno virtual


uvicorn app.main:app --port 3001 --reload
alembic init migrations
alembic revision --autogenerate -m "Initial migration"

alembic revision --autogenerate -m "Added comments table"
alembic upgrade head
