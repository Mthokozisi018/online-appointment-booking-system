# GreenChoice / GreenConnect

GreenChoice is a staff-only inventory management system for the GreenChoice MVP. Customers do not log in.

The current system is split into:

- `booking_system/` and `careconnect_v2_api/`: Django REST Framework backend under `/api/v2/`
- `greenchoice-workstation/`: Next.js frontend deployed to Vercel
- `render.yaml`: Render blueprint for the hosted Django API and PostgreSQL database

## Staff Roles

The MVP supports two staff roles:

- `MANAGER`
- `RECEPTIONIST`

A manager can later create receptionist accounts inside the app. The first manager is seeded by a developer/admin setup command.

## Local Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_greenchoice_staff
python manage.py seed_greenchoice_demo
python manage.py runserver
```

The local API runs at `http://127.0.0.1:8000/api/v2`.

## Local Frontend

```powershell
cd greenchoice-workstation
npm install
npm run dev
```

Open `http://127.0.0.1:3001/login`.

## Development Staff Logins

Development manager:

- Email: `manager@greenchoice.local`
- Password: `ChangeMe123!`
- Role: `MANAGER`

Development receptionist, created by `seed_greenchoice_demo`:

- Email: `receptionist@greenchoice.local`
- Password: `ChangeMe123!`
- Role: `RECEPTIONIST`

These credentials are only for development/testing. Change seeded passwords before using the system in production.

## GreenChoice Routes

Frontend:

- `/login`
- `/dashboard/manager`
- `/dashboard/manager/products`
- `/dashboard/manager/products/new`
- `/dashboard/manager/products/category/[slug]`
- `/dashboard/manager/inventory`
- `/dashboard/manager/sales`
- `/dashboard/manager/staff`
- `/dashboard/manager/low-stock`
- `/dashboard/manager/promotions`
- `/dashboard/manager/categories`
- `/dashboard/receptionist`
- `/dashboard/receptionist/products`
- `/dashboard/receptionist/customers/register`
- `/dashboard/receptionist/checkout`

Backend:

- `POST /api/v2/auth/login/`
- `POST /api/v2/auth/logout/`
- `GET /api/v2/auth/me/`
- `GET /api/v2/greenchoice/categories/`
- `GET /api/v2/greenchoice/products/`
- `GET /api/v2/greenchoice/manager/summary/`
- `GET /api/v2/greenchoice/manager/inventory/`
- `GET /api/v2/greenchoice/manager/low-stock/`
- `GET /api/v2/greenchoice/manager/sales/`
- `GET /api/v2/greenchoice/manager/staff/`
- `GET /api/v2/greenchoice/manager/promotions/`
- `GET/POST /api/v2/greenchoice/customers/`

Manager endpoints require `MANAGER`. Product/category browsing and customer record creation require GreenChoice staff. A `RECEPTIONIST` receives `403` on manager-only endpoints.

## Production Deployment

Frontend production URL:

```text
https://greenchoice-workstation.vercel.app
```

The frontend must set:

```text
GREENCHOICE_API_BASE_URL=https://greenchoice-api.onrender.com/api/v2
APP_URL=https://greenchoice-workstation.vercel.app
CSRF_SECRET=<long random secret>
SESSION_SIGNING_SECRET=<long random secret>
STAFF_SESSION_SIGNING_SECRET=<long random secret>
```

The backend must set:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<long random secret>
DJANGO_ALLOWED_HOSTS=greenchoice-api.onrender.com
DATABASE_URL=<managed postgres connection string>
DATABASE_SSL_REQUIRE=true
FRONTEND_URL=https://greenchoice-workstation.vercel.app
GREENCHOICE_FRONTEND_URL=https://greenchoice-workstation.vercel.app
CORS_ALLOWED_ORIGINS=https://greenchoice-workstation.vercel.app
CSRF_TRUSTED_ORIGINS=https://greenchoice-workstation.vercel.app
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

Render can create the backend and PostgreSQL database from `render.yaml`. The blueprint runs migrations and seed commands during deploy:

```powershell
python manage.py migrate
python manage.py seed_greenchoice_staff
python manage.py seed_greenchoice_demo
```

## Verification

1. Open `https://greenchoice-workstation.vercel.app/login`.
2. Log in as `manager@greenchoice.local` with `ChangeMe123!`.
3. Confirm the manager reaches `/dashboard/manager`.
4. Log out, then log in as `receptionist@greenchoice.local` with `ChangeMe123!`.
5. Confirm the receptionist reaches `/dashboard/receptionist`.
6. Confirm old recommendation routes like `/browse` and `/register` redirect to `/login`.
