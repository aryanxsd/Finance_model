# Finance Data Processing and Access Control Backend

A complete backend assignment submission built from scratch with Flask and SQLite. It demonstrates:

- User and role management
- Backend-enforced access control
- Financial record CRUD with filtering, search, and pagination
- Dashboard summary and trend APIs
- Input validation and consistent error handling
- Simple rate limiting middleware
- Persistent local storage with seeded demo data
- Automated tests using Python `unittest`

## Tech stack

- Python 3.12
- Flask 3
- SQLite via the standard library `sqlite3`

## Project structure

```text
finance_dashboard_backend/
|-- finance_api/
|   |-- __init__.py
|   |-- auth.py
|   |-- config.py
|   |-- db.py
|   |-- permissions.py
|   |-- validation.py
|   `-- routes/
|       |-- dashboard.py
|       |-- records.py
|       `-- users.py
|-- tests/
|   `-- test_api.py
|-- requirements.txt
`-- run.py
```

## Features mapped to the assignment

### User and role management

- Create, list, view, and update users
- Roles supported: `viewer`, `analyst`, `admin`
- User status supported: `active`, `inactive`
- Token-based mock authentication using `Authorization: Bearer <token>`
- Role restrictions enforced at the backend layer

### Financial records management

- Create, list, fetch, update, and soft-delete financial records
- Record fields: amount, type, category, date, notes
- Filtering supported on `type`, `category`, `start_date`, and `end_date`
- Search supported with `search` against category and notes
- Pagination supported with `page` and `page_size`

### Dashboard summary APIs

- Total income
- Total expenses
- Net balance
- Category-wise totals
- Recent activity
- Monthly trends

### Access control rules

- `viewer`: can only access dashboard endpoints
- `analyst`: can access dashboard endpoints and read financial records
- `admin`: full access to user management and financial record management

### Validation and reliability

- Request body validation
- Query validation
- Proper status codes
- Consistent JSON error payloads
- Simple rate limiting with HTTP `429` responses when limits are exceeded

### Data persistence

- Uses SQLite persisted to `finance_dashboard.db`
- Automatically creates tables and seeds demo data on first run

## Setup

Clone the repository and move into the project folder:

```bash
git clone https://github.com/aryanxsd/Finance_model.git
cd Finance_model
```

## Create a virtual environment

### On WSL / Ubuntu / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### On Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### On Windows Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

## Install dependencies

```bash
python -m pip install -r requirements.txt
```

## Run the application

```bash
python run.py
```

The server starts on `http://127.0.0.1:5000`.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Notes

- If `python` is not available on WSL or Linux, use `python3`.
- The application uses SQLite for persistence and creates the local database automatically on first run.
- Seeded demo users are created automatically for testing.

## Seeded users

These are created automatically on first startup:

| Role | Email | Token |
|---|---|---|
| Viewer | `viewer@finance.local` | `viewer-token` |
| Analyst | `analyst@finance.local` | `analyst-token` |
| Admin | `admin@finance.local` | `admin-token` |

## API overview

Postman collection:

- `postman/Finance_model.postman_collection.json`

### Health

- `GET /health`

### Authentication

Use either:

- `Authorization: Bearer <token>`
- `X-API-Token: <token>`

### User APIs

- `GET /api/users` - admin only
- `POST /api/users` - admin only
- `GET /api/users/<id>` - admin only
- `PATCH /api/users/<id>` - admin only
- `GET /api/users/me` - any authenticated user

### Financial record APIs

- `GET /api/records` - analyst or admin
- `POST /api/records` - admin only
- `GET /api/records/<id>` - analyst or admin
- `PATCH /api/records/<id>` - admin only
- `DELETE /api/records/<id>` - admin only

### Dashboard APIs

- `GET /api/dashboard/summary`
- `GET /api/dashboard/recent-activity`
- `GET /api/dashboard/trends`

All dashboard endpoints are available to `viewer`, `analyst`, and `admin`.

## Optional enhancements completed

- Token-based authentication
- Pagination for record listing
- Search support for records
- Soft delete functionality
- Rate limiting
- Automated tests
- API documentation in this README

## Sample requests

### Fetch dashboard summary as viewer

```bash
curl -H "Authorization: Bearer viewer-token" http://127.0.0.1:5000/api/dashboard/summary
```

### List income records as analyst

```bash
curl -H "Authorization: Bearer analyst-token" "http://127.0.0.1:5000/api/records?type=income"
```

### Search and paginate records as analyst

```bash
curl -H "Authorization: Bearer analyst-token" "http://127.0.0.1:5000/api/records?search=consulting&page=1&page_size=5"
```

### Create a financial record as admin

```bash
curl -X POST http://127.0.0.1:5000/api/records \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-token" \
  -d "{\"amount\": 5200, \"type\": \"income\", \"category\": \"Consulting\", \"date\": \"2026-03-25\", \"notes\": \"Architecture advisory\"}"
```

### Create a user as admin

```bash
curl -X POST http://127.0.0.1:5000/api/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-token" \
  -d "{\"name\": \"Naina Viewer\", \"email\": \"naina@example.com\", \"role\": \"viewer\", \"status\": \"active\"}"
```

## Design notes and assumptions

- Authentication is intentionally lightweight and mock-friendly for the assessment.
- Tokens are stored directly in the database to keep the project simple and easy to review.
- Financial record deletion is implemented as a soft delete so deleted rows do not appear in summaries or listings.
- Rate limiting is implemented in memory, which is appropriate for a local assessment project but not intended as a distributed production solution.
- The app uses modular route files plus shared auth, permission, database, and validation layers for maintainability.
- SQLite was chosen for portability and zero-config local setup.

## Submission notes

This project directly addresses the assignment requirements through:

- Clear route and service separation
- Explicit role-based authorization
- Aggregation endpoints for dashboard use cases
- Reliable validation and status codes
- Persistent data storage
- A README that explains assumptions, setup, and API behavior
