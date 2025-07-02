# Todo Application

A full-stack todo application built with FastAPI (backend) and React (frontend).

## Features

- ✅ Create, read, update, and delete todos
- 🏷️ Priority levels (low, medium, high)
- 📅 Due dates
- 🔍 Search and filter todos
- 📱 Responsive design
- 🐳 Docker support
- ☁️ AWS deployment ready

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL/SQLite
- Pydantic
- Uvicorn

### Frontend
- React 18
- Vite
- Axios
- date-fns

### DevOps
- Docker
- Docker Compose
- AWS (ECS, RDS, ALB)
- GitHub Actions

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend will be available at http://localhost:8000

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:3000

### Docker Development

```bash
docker-compose up
```

Application will be available at http://localhost

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Deployment

See [deployment/AWS_DEPLOYMENT.md](deployment/AWS_DEPLOYMENT.md) for detailed AWS deployment instructions.

### Quick Deploy with Docker

1. Build images:
```bash
docker build -t todo-backend ./backend
docker build -t todo-frontend ./frontend
```

2. Run with environment variables:
```bash
docker run -d -p 8000:8000 -e DATABASE_URL=your_db_url todo-backend
docker run -d -p 80:80 todo-frontend
```

## Environment Variables

### Backend
- `DATABASE_URL`: PostgreSQL connection string (default: SQLite)
- `SECRET_KEY`: Secret key for security
- `CORS_ORIGINS`: Allowed CORS origins

### Frontend
- `VITE_API_URL`: Backend API URL (default: /api)

## Project Structure

```
todo-app/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Database configuration
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx     # Main React component
│   │   ├── components/ # React components
│   │   └── main.jsx    # Entry point
│   ├── package.json
│   └── vite.config.js
├── tests/              # Unit tests
├── deployment/         # Deployment configurations
└── docker-compose.yml
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.
EOF < /dev/null