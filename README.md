# Multi-Vendor Event Ticketing API

A Django backend, built with production concerns in mind, for event platforms where multiple vendors sell tickets to the same shows without stepping on each other's toes—literally. No overselling, no race conditions, no 2am support calls about double-charged customers.

## Live Demo & Documentation

Experience the API directly through the live production environment. You can explore interactive endpoints, test requests, and view full schema specifications without setting up a local environment.

https://multi-vendor-event-ticketing-reservation-api-production.up.railway.app/api/docs/

## Why I built this

I got tired of systems that *looked* concurrent-safe until they weren't. Ticket platforms are a perfect storm: high volume, tight inventory, money involved, and everyone buying tickets at the exact same moment. Most examples online either ignore this entirely or hand-wave it away.

This project treats concurrency as a first-class problem. The database row-level locking isn't a band-aid—it's the foundation. Real Stripe integration means we're not pretending payment is simple. And the notification system is decoupled because email should never block a customer's purchase confirmation.

It's not a toy. It's also not overengineered for problems that don't exist yet.

## What makes this different

**Atomic reservations under load.** Two customers can't both grab the last ticket because `SELECT FOR UPDATE` locks the row, and PostgreSQL enforces it. You can hammer this with concurrent requests and inventory stays correct.

**Stripe done right.** This uses webhook signature verification, idempotent payment updates (same webhook called twice? doesn't matter), and embeds payment metadata in a way that doesn't trust the client. No accidental double-charging because a webhook retried.

**Notifications that don't break the system.** When someone buys a ticket, a job goes onto Redis. A separate FastAPI service picks it up and sends the email. If email is slow, timing out, or down? The ticket purchase already completed. Customers see their confirmation instantly.

**Tickets have a real lifecycle.** Reserved → Purchased → Used → Cancelled. A scheduled task automatically expires unpaid reservations after a timeout so seats don't get held indefinitely. The state machine isn't just in comments; it's enforced in the database.

**Built for humans.** Soft deletes so you never accidentally nuke data. Check constraints at the database level so bad data can't sneak in. JWT authentication that actually works. Role-based permissions—organizers can only see their own events. The API docs auto-generate from code and stay up-to-date.

## Architecture

**The ticket API** handles reservations, payments, and all the business logic. It talks to PostgreSQL (where row-level locking keeps inventory safe from race conditions).

When a ticket sells, instead of trying to send an email right there, the API just drops an event onto a Redis queue. Done. The customer sees their confirmation instantly.

**The notification service** sits on the other end of that Redis queue. It's a separate FastAPI app that pulls events and sends emails. If email is slow, timing out, or the service is down for maintenance—doesn't matter. The ticket purchase already happened. Customers never see the delay.

This split means:
- Scale the ticket API independently of email sending
- Emails never block a purchase (slow SMTP server? not your problem)
- You can deploy, restart, or update each service without touching the other
- Easy to test—mock the Redis queue and both services work offline

See the [notification service repo](https://github.com/Eng0-0Ahmed/Notification-Service) for the email half of this.

## Quick start

### Prerequisites
- Docker & Docker Compose
- Or: Python 3.11+, PostgreSQL, Redis

### Running locally

```bash
git clone <https://github.com/Eng0-0Ahmed/Multi-Vendor-Event-Ticketing-Reservation-API>
cd event-ticketing
cp .env.example .env
docker compose up --build
```

In a separate terminal, run migrations (not automatic on container startup):

```bash
docker compose exec web python manage.py migrate
```

API is at `http://localhost:8000/`. Docs are at `/api/docs/`.

### First time setup

```bash
# Run migrations (not automatic on startup — do this first)
docker compose exec web python manage.py migrate

# Create a superuser for the admin panel
docker compose exec web python manage.py createsuperuser
```

## Environment variables

Copy `.env.example` and fill in your values:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=ticketing
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis (for task queue)
REDIS_HOST=redis
REDIS_PORT=6379

# Stripe (get these from your Stripe dashboard)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Note: this service and the notification service don't talk over HTTP —
they're only connected through the shared Redis queue (`REDIS_HOST`/
`REDIS_PORT` above), so there's no notification service URL to configure
here.

## API overview

Interactive documentation once the server is running:

- **Swagger UI:** `http://localhost:8000/api/docs/`
- **ReDoc:** `http://localhost:8000/api/redoc/`
- **OpenAPI schema:** `http://localhost:8000/api/schema/`

### Core endpoints

**Authentication**
```
POST   /api/users/register/              Create account
POST   /api/users/token/                 Get JWT tokens
POST   /api/users/token/refresh/         Refresh access token
```

**Events** (as an organizer)
```
GET    /api/events/                      List all events
POST   /api/events/create/               Create a new event (organizer only)
GET    /api/events/{id}/                 Get event details
PATCH  /api/events/{id}/edit             Update your event
```

**Tickets**
```
GET    /api/tickets/types/               List ticket types for an event
POST   /api/tickets/types/{id}/reserve/  Reserve a ticket (holds it for 10 mins)
POST   /api/tickets/{id}/checkout/       Create Stripe checkout session
POST   /api/tickets/verify/              Verify/check-in a ticket (QR data in request body)
```

**Webhooks** (Stripe only)
```
POST   /api/tickets/stripe/webhook/      Stripe payment updates
```

See the Swagger docs for the full list, response formats, and what each field means.

## Real-world example: buying a ticket

```bash
# 1. Get an access token
curl -X POST http://localhost:8000/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'

# Response includes access_token

# 2. Reserve a ticket type (holds for 10 minutes)
curl -X POST http://localhost:8000/api/tickets/types/42/reserve/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 1}'

# Response: ticket ID, expiry time, price

# 3. Create a Stripe checkout session
curl -X POST http://localhost:8000/api/tickets/123/checkout/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Response: redirect_url

# 4. User goes to Stripe, pays
# Stripe webhook comes back → ticket marked purchased → email sent

# 5. User gets a ticket they can scan at the door
```

## Testing

Run the test suite locally:

```bash
python manage.py test
```

Or in Docker:

```bash
docker compose exec web python manage.py test
```

Tests cover:
- Concurrent reservation scenarios (the hard part)
- Stripe webhook handling and idempotency
- User permissions and authentication
- State machine transitions
- Edge cases like expired reservations

## How concurrency actually works

When a customer reserves a ticket:

```python
with transaction.atomic():
    ticket_type = TicketType.objects.select_for_update().get(id=type_id)
    
    if ticket_type.available_count > 0:
        reservation = Reservation.objects.create(ticket_type=ticket_type, ...)
        ticket_type.available_count -= 1
        ticket_type.save()
    else:
        raise OutOfStock()
```

The `select_for_update()` locks the row at the database level. Other transactions *wait* until this one finishes. No two customers can both see 1 ticket left and both reserve it.

This isn't magic—it's just how databases work. But it matters because most tutorials don't bother.

## Stripe integration details

When payment completes:

1. Stripe calls our webhook with a cryptographic signature
2. We verify the signature against `STRIPE_WEBHOOK_SECRET` (not trusting the request itself)
3. We mark the reservation as purchased and create the actual ticket
4. We push a notification event onto Redis
5. The notification service picks it up and sends the email

If the webhook comes in twice (Stripe retries), we idempotently update the same ticket. No duplicate charges, no double emails.

## Design decisions

**Stripe Checkout redirect instead of embedded form.** This is intentional. Embedded checkout adds complexity, requires careful PCI compliance thinking, and the redirect approach is battle-tested. Simplicity over false convenience.

**Row-level database locking for concurrency.** This works. It scales. It's boring in the best way. I didn't add Redis-based locking or distributed consensus because the database already does this correctly.

**Vendor signup without verification.** The system is built to support a verification flow—you'd add identity checks, email verification, and manual approval without touching core logic. Left it out because it's not part of what makes this interesting technically.

## Deployment

The included `docker-compose.yml` is for local development. For production:

- Use a managed PostgreSQL instance (AWS RDS, Render, Railway, etc.)
- Use a managed Redis (AWS ElastiCache, Render, etc.)
- Swap Docker Compose for Kubernetes, Docker Swarm, or a platform like Railway/Render
- Set `DEBUG=False` and use a real `SECRET_KEY`
- Set up SSL/TLS (handled by your reverse proxy or platform)
- Run migrations before deploying: `python manage.py migrate`
- Collect static files: `python manage.py collectstatic --noinput`

## License

MIT

## Questions?

Open an issue or check the Swagger docs at `/api/docs/` for endpoint details.
