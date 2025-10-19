# Construction Expense Tracker

A comprehensive Django-based web application for managing multiple construction projects and tracking expenses effectively. This production-ready application provides an intuitive dashboard, project management tools, and visual performance summaries.

## Features

### 🏗️ **Project Management**
- Create and manage multiple construction projects
- Track project status, timelines, and budgets
- Monitor progress with visual indicators
- Client information management
- Project-contractor assignments

### 💰 **Expense Tracking**
- Track planned vs actual costs
- Categorize expenses by type
- Receipt and document management
- Contractor expense assignments
- Tax information tracking
- Recurring expense templates

### 👷 **Contractor Management**
- Maintain contractor database
- Track contractor ratings and performance
- Manage contractor types and specializations
- Hourly rate and licensing information

### 📊 **Dashboard & Analytics**
- Interactive KPI dashboard
- Visual charts and graphs
- Monthly expense trends
- Project status overview
- Budget variance tracking
- Quarterly summaries

### 🚀 **Production Ready**
- Docker containerization
- PostgreSQL database support
- Redis for caching and tasks
- Gunicorn WSGI server
- WhiteNoise for static files
- Comprehensive admin interface

## Quick Start

### Option 1: Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd construction_expense_tracker
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Visit the application**
   - Application: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

### Option 2: Docker Development

1. **Clone and start with Docker**
   ```bash
   git clone <repository-url>
   cd construction_expense_tracker
   docker-compose up --build
   ```

2. **Run migrations in container**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Visit the application**
   - Application: http://localhost:8000/
   - Admin: http://localhost:8000/admin/

## Production Deployment

### Docker Production Setup

1. **Create production environment file**
   ```bash
   cp .env .env.production
   # Configure production settings in .env.production
   ```

2. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

### Manual Production Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install gunicorn whitenoise
   ```

2. **Configure environment**
   ```bash
   export DEBUG=False
   export DATABASE_URL=postgres://user:password@host:port/database
   export SECRET_KEY=your-secret-key
   ```

3. **Run migrations and collect static**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

4. **Start with Gunicorn**
   ```bash
   gunicorn --bind 0.0.0.0:8000 construction_tracker.wsgi:application
   ```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Basic settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
DATABASE_URL=sqlite:///db.sqlite3
# For PostgreSQL: postgres://username:password@host:port/database_name

# Email settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Static and media files
STATIC_ROOT=staticfiles
MEDIA_ROOT=media

# CORS settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Database Models

### Core Models
- **UserProfile**: Extended user information
- **TimeStampedModel**: Abstract base with timestamps

### Project Models
- **Project**: Main project information
- **ProjectContractor**: Project-contractor relationships

### Expense Models
- **ExpenseCategory**: Expense categorization
- **Expense**: Individual expense records
- **ExpenseAttachment**: File attachments
- **RecurringExpense**: Recurring expense templates

### Contractor Models
- **Contractor**: Contractor information and ratings

## API Endpoints

The application includes REST API endpoints for integration:

- **Projects**: `/api/projects/`
- **Expenses**: `/api/expenses/`
- **Contractors**: `/api/contractors/`
- **Categories**: `/api/categories/`

## Admin Interface

Access the comprehensive admin interface at `/admin/` to:

- Manage users and permissions
- Create and edit projects
- Track expenses and categories
- Manage contractor information
- View calculated fields and statistics

## Testing

Run the test suite:

```bash
python manage.py test
```

With coverage:

```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

## Development

### Adding New Features

1. Create feature branch
2. Add models to appropriate app
3. Create and run migrations
4. Add views and templates
5. Update URLs
6. Add tests
7. Update documentation

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# View migration status
python manage.py showmigrations
```

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check DATABASE_URL in .env
   - Ensure PostgreSQL is running (if using)

2. **Static files not loading**
   - Run `python manage.py collectstatic`
   - Check STATIC_ROOT setting

3. **Permission denied errors**
   - Check file permissions
   - Ensure media directory is writable

4. **Docker build issues**
   - Clear Docker cache: `docker system prune`
   - Rebuild: `docker-compose up --build`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the admin interface for data management

## Technology Stack

- **Backend**: Django 5.2, Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Bootstrap 5, Chart.js
- **Caching**: Redis
- **Task Queue**: Celery
- **Deployment**: Docker, Gunicorn
- **Static Files**: WhiteNoise
