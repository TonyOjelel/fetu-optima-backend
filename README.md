# FETU Optima Backend

A high-performance, scalable backend for the FETU Optima intellectual challenge platform. Built with FastAPI, PostgreSQL, and Redis.

## Features

- 🔐 Secure JWT Authentication with optional 2FA
- 🧩 AI-powered puzzle generation engine
- 🏆 Real-time leaderboard with WebSocket support
- 💰 Mobile Money integration (MTN/Airtel)
- 📊 Advanced analytics and user behavior tracking
- ⚡ High-performance REST API
- 🔄 Real-time updates and notifications
- 📈 Scalable architecture with modular design

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Caching**: Redis
- **Authentication**: JWT + Optional 2FA
- **Real-time**: WebSockets
- **Documentation**: OpenAPI (Swagger)
- **Testing**: Pytest
- **Monitoring**: Prometheus + Sentry

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/TonyOjelel/fetu-optima-backend.git
   cd fetu-optima-backend
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

Visit `http://localhost:8000/docs` for interactive API documentation.

## Project Structure

```
fetu-optima-backend/
├── alembic/              # Database migrations
├── app/
│   ├── api/             # API endpoints
│   ├── core/            # Core functionality
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── utils/           # Utility functions
├── tests/               # Test suite
└── docker/              # Docker configuration
```

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.