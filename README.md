# Hospital Appointment Booking System

## Project structure

```text
Hospital Appointment Booking System/
│
├── alembic/
│   └── versions/
│
├── app/
│   ├── auth/
│   ├── jobs/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   ├── websockets/
│   └── __init__.py
│
├── static/
├── Screenshots/
├── uploads/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── README.md
└── app/main.py
```

## WebSocket queue testing

Start the API using the project's configured environment, then obtain an **access**
token by signing in. WebSocket endpoints are not listed in Swagger.

### Postman

1. Create a WebSocket request to
   `ws://localhost:8000/ws/queue/1?token=<access_token>` (replace `1` with a
   valid doctor ID and provide the access token without angle brackets).
2. Connect. The first message is that user's queue snapshot.
3. Check in an appointment or call the next patient through the API. The
   updated queue snapshot should arrive on the open connection.
4. To test personal notifications, connect to
   `ws://localhost:8000/ws/notifications?token=<access_token>`, then book,
   reschedule, or cancel an appointment for that user. The corresponding event
   should appear as a message.

Use `wss://` instead of `ws://` when the API is served over HTTPS. An invalid
or expired access token is rejected with WebSocket close code `4401`.

### Browser console

Open the browser developer console on `http://localhost:8000` and run this
snippet, replacing the token and doctor ID:

```javascript
const token = "<access_token>";
const ws = new WebSocket(
  `ws://localhost:8000/ws/queue/1?token=${encodeURIComponent(token)}`
);
ws.onmessage = (event) => console.log("Queue update:", JSON.parse(event.data));
ws.onclose = (event) => console.log("Closed:", event.code, event.reason);
```

Open another browser tab with a different user's token to confirm that both
connected users receive queue updates.

### HTML test page

Open [http://localhost:8000/queue-test](http://localhost:8000/queue-test), select
the queue or personal-notifications connection, enter the access token and
doctor ID when applicable, and click **Connect**. Messages and close codes are
shown on the page. Do not use this page on a shared or public machine with a
real access token.

### Queue behavior

- Queue snapshots are scoped to today's appointments and include the current
  token, the number of checked-in patients waiting, and the connected patient's
  token, position, and estimated wait when checked in.
- Estimated wait is the count of appointments ahead (including an earlier
  appointment currently in consultation) multiplied by the doctor's slot
  duration.
- The doctor can call the next checked-in patient only when no appointment is
  currently in consultation. Saving the consultation completes the current
  appointment and broadcasts the changed queue.
- Check-in, cancellation, rescheduling, booking, consultation completion, and
  scheduled no-show changes broadcast an updated queue.
- Booking, cancellation, and rescheduling send personal notification events;
  calling the next patient sends that patient a `your_turn` event.
## Local setup

1. Install Python 3.9 or newer and MySQL 8.
2. Create a MySQL database named `hospital_booking`.
3. Create and activate a virtual environment.
4. Install dependencies with `pip install -r requirements.txt`.
5. Copy `.env.example` to `.env` and set the database URL, a long random JWT secret, and SMTP credentials.
6. Apply migrations with `alembic upgrade head`.
7. Start the API with `uvicorn app.main:app --reload`.
8. Open `http://localhost:8000/docs` to test the REST endpoints.

Do not commit `.env` or the `uploads/` directory. The sample values in `.env.example` are placeholders and must be replaced before deployment.

## Staff account creation

Public `POST /auth/register` always creates a patient. An authenticated Admin creates a Doctor or another Admin account with `POST /auth/users`. The Doctor profile is then created with `POST /doctors`, using the staff account's `user_id`.

## Database migrations

Run `alembic upgrade head` after updating the code. To inspect the current revision, run `alembic current`. Do not create tables with SQLAlchemy `create_all()` in the application startup.

## Automated tests

Run `pytest -q`. The test suite validates request schemas, role input restrictions, timestamp columns, and ORM relationship configuration. Run integration tests against a dedicated MySQL test database before production deployment.
