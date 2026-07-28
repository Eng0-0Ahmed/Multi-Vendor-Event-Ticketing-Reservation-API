# Multi-Vendor Event Ticketing & Reservation API

A production-ready Django REST Framework API for multi-vendor event ticketing, dynamic seat reservations, Stripe checkout integration, automated QR-code generation, and venue entry verification.

**Live Interactive API Documentation (Swagger):** [ahmedaymen00.pythonanywhere.com/api/docs/](https://ahmedaymen00.pythonanywhere.com/api/docs/)

---

## Overview

This API powers a scalable event management platform. Multiple vendors can publish and manage events, users can securely reserve and purchase tickets, and venue staff can verify tickets at the door using QR code scanning.

---

## Key Features & Technical Highlights

* **Multi-Vendor Management:** Role-based permissions allowing vendors to publish events, adjust capacities, and track ticket availability.
* **Race-Condition & Double-Booking Guards:** Uses atomic database transactions (`transaction.atomic`) and row-level locking (`select_for_update`) with expiring reservation timers to prevent double-booking during high-concurrency ticket drops.
* **Stripe Payment & Webhook Processing:** Integrates Stripe Checkout with asynchronous webhook handling (`checkout.session.completed`) using cryptographic signature verification to ensure secure order fulfillment.
* **Automated QR Generation & Email Delivery:** Automatically generates unique QR codes upon payment confirmation and emails tickets directly to buyers.
* **Gate Verification Endpoint:** Fast indexed lookup endpoint (`POST /api/tickets/verify/`) for venue staff to validate scanned QR codes and prevent reuse.
* **Comprehensive Test Suite:** Unit and integration tests covering authentication, event creation, locking logic, and checkout flows across all modules (`users`, `events`, and `tickets`).
* **Interactive API Docs:** Auto-generated OpenAPI 3.0 schema and interactive Swagger UI powered by `drf-spectacular`.

---

## Tech Stack

* **Language:** Python 3.12+
* **Framework:** Django 5 & Django REST Framework (DRF)
* **Database:** SQLite (Development) / PostgreSQL (Production)
* **Libraries & Integrations:** Stripe API, Pillow, `qrcode`
* **Documentation:** `drf-spectacular` (Swagger UI)
* **Formatting:** `black`

---

## Key API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/users/register/` | Register a new user account | No |
| `GET` | `/api/events/` | List all published events | No |
| `POST` | `/api/tickets/types/<uuid>/reserve/` | Reserve a ticket tier (Row-locked) | Yes |
| `POST` | `/api/tickets/<uuid>/checkout/` | Create a Stripe Checkout session | Yes |
| `POST` | `/api/tickets/stripe/webhook/` | Listen for Stripe payment events | No (Stripe Sig) |
| `POST` | `/api/tickets/verify/` | Scan and verify venue QR code | Staff / Vendor |
| `GET` | `/api/docs/` | Interactive Swagger API documentation | No |

---

## Getting Started

### 1. Installation & Setup

Clone the repository and enter the directory:
\`\`\`bash
git clone https://github.com/Eng0-0Ahmed/Multi-Vendor-Event-Ticketing-Reservation-API.git
cd Multi-Vendor-Event-Ticketing-Reservation-API
\`\`\`

Set up and activate a virtual environment:
\`\`\`bash
# On Windows:
python -m venv venv
venv\Scripts\activate

# On Mac/Linux:
python3 -m venv venv
source venv/bin/activate
\`\`\`

Install dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

Set up environment variables:
\`\`\`bash
# Copy example env file
cp .env.example .env
\`\`\`

Run database migrations and start the development server:
\`\`\`bash
python manage.py migrate
python manage.py runserver
\`\`\`

Access the interactive API documentation at `http://127.0.0.1:8000/api/docs/`.

---

## Running Tests

To run the full test suite across all apps (`users`, `events`, and `tickets`):
\`\`\`bash
python manage.py test
\`\`\`