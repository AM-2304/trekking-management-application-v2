# Trekking Management Application (TMA)

A web application for managing trekking activities, with three roles: Admin, Trek Staff
and User (Trekker).

Built with Flask, Vue 3, Bootstrap 5, SQLite, Redis and Celery. There is no Node build
step — Vue and Bootstrap are served as plain files from `app/static/vendor/`, so the
project runs with no internet connection and nothing to compile.

---

## Quick start

### 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create and populate the database

```bash
flask --app run.py seed
```

This creates `instance/tma.db` from the model definitions and adds the single
administrator plus demo data. Nothing is created by hand.

### 3. Start Redis

```bash
redis-server
```

### 4. Start the Celery worker and scheduler

```bash
celery -A celery_worker.celery worker --beat --pool=solo --loglevel=info
```

> **`--pool=solo` matters.** Celery's default "prefork" pool forks worker processes,
> which fails on macOS with
> `ValueError: not enough values to unpack (expected 3, got 0)`.
> The solo pool runs tasks in a single process and avoids the problem entirely. It is
> also easier to reason about: one process, one task at a time.

### 5. Start the web application

```bash
python run.py
```

Open <http://127.0.0.1:5000>.

---

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@tma.local` | `admin123` |
| Trek Staff | `vikram@tma.local` | `staff123` |
| User (Trekker) | `amit@tma.local` | `user123` |

The login page has shortcut links that fill these in.

Other seeded staff: `neha@tma.local`, `arjun@tma.local`.
Other seeded trekkers: `priya@tma.local`, `rahul@tma.local`, `sneha@tma.local`.

---

## Running the tests

```bash
pytest -v
```

Ten tests cover the rules that would be invisible in a quick demo: the booking guard
(including twelve threads racing for three seats), duplicate bookings, cancellation
returning a slot, role-based access control, the assigned-staff ownership check, and
immediate rejection of a blacklisted account.

---

## What each piece does

| Path | Purpose |
|---|---|
| `run.py` | Flask entry point |
| `celery_worker.py` | Celery entry point |
| `app/__init__.py` | Application factory, SQLite pragmas, blueprint registration |
| `app/config.py` | All configuration, read from environment variables |
| `app/models.py` | The three tables: User, Trek, Booking |
| `app/auth.py` | Session login, registration, and the role decorators |
| `app/routes_admin.py` | Admin API |
| `app/routes_staff.py` | Trek staff API |
| `app/routes_user.py` | Trekker API, including the booking guard |
| `app/cache.py` | Redis caching helper |
| `app/mailer.py` | Writes mail to `instance/outbox/`, or sends over SMTP |
| `app/tasks.py` | The three Celery jobs |
| `app/seed.py` | `flask seed` and `flask init-db` |
| `app/templates/index.html` | The only Jinja2 template — the Vue entry point |
| `app/static/js/` | The Vue application |

---

## Background jobs

| Job | Schedule | What it does |
|---|---|---|
| Daily reminders | 08:00 daily | Emails trekkers whose trek starts within 3 days |
| Monthly activity report | 1st of the month, 09:00 | Emails the admin an HTML activity summary |
| CSV export | On demand | Writes a trekker's booking history to a CSV file |

Mail is written to `instance/outbox/` as HTML files by default, so no mail server is
needed. Set `MAIL_BACKEND=smtp` to send for real.

**You do not have to wait for a schedule.** Sign in as the admin and open
**Reports** to run the two scheduled jobs immediately. The CSV export is triggered from
the trekker's **Profile** screen.

---

## Caching

Only two things are cached, both in Redis:

| Key | TTL |
|---|---|
| `tma:treks:<hash>` — a page of browse results | 60 s |
| `tma:admin:stats` — the dashboard counts | 30 s |

Watch it work:

```bash
redis-cli KEYS 'tma:*'
redis-cli TTL tma:admin:stats
```

Anything involving slot counts or bookings is deliberately **never** cached, because a
stale slot count would let the application oversell a trek. Every trek write and every
booking clears both key groups.

If Redis is not running the application still works — the cache helper treats an error
as a cache miss.

---

## Preventing overbooking

Two people clicking "Book now" at the same instant must not both get the last seat.
Booking takes a seat with a single conditional statement:

```sql
UPDATE trek SET available_slots = available_slots - 1
WHERE id = ? AND available_slots > 0 AND status = 'Open'
```

SQLite applies that atomically, so of two racing requests exactly one sees
`rowcount == 1` and the other sees `0` and is told the trek is full.

The obvious alternative — read the count, check it in Python, then write — is broken:
under WAL journalling a transaction that upgrades from a read lock to a write lock fails
immediately with `database is locked`, and `busy_timeout` cannot retry out of it.

A test reproduces the race with twelve concurrent threads.

---

## Notes

- The database is created entirely from model code (`db.create_all()`), including the
  partial unique index that prevents duplicate active bookings.
- There is exactly one administrator, created by `flask seed`. There is no admin
  registration, and only trekkers can register themselves.
- `instance/` holds the database, the mail outbox and generated CSV files. It is
  git-ignored.
