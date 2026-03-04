# Email Campaign Manager

A production-ready Email Campaign Manager backend built with Django and Django REST Framework. This application allows you to manage subscribers, create email campaigns, and schedule them for delivery. It uses a robust, multithreaded architecture for dispatching emails securely and efficiently while avoiding race conditions.

## Tech Stack

- **Backend Framework**: Django 4.2+
- **API Framework**: Django REST Framework (DRF)
- **Concurrency & Parallelization**: Python's `threading` and `queue` (Implementing a Publisher-Subscriber pattern)
- **Database**: SQLite (default, production ready schema, easily swap to PostgreSQL)
- **Task Automation**: Django Custom Management Commands
- **Environment Management**: `python-dotenv`

## Implementation Checklist & Methods

Below is a breakdown of how the requested tasks were implemented:

1. **Add Subscribers ('email', 'first_name')**
   - **Implementation:** Created the `Subscriber` model and mapped it to a DRF view. You can add users programmatically via the `POST /api/subscribers/` endpoint or manually via the Django Admin. 

2. **Endpoint to unsubscribe users & Mark as "inactive"**
   - **Implementation:** Created the `POST /api/unsubscribe/` endpoint. Instead of hard-deleting the user from the database, it performs a soft-delete by setting `is_active=False` and recording the time in `unsubscribed_at`.

3. **Use Django admin to add new records to each table**
   - **Implementation:** Registered `Subscriber`, `Campaign`, and `EmailLog` models inside `campaigns/admin.py`. Logging into `/admin/` allows you to manage all models visually with proper permission handling.

4. **Write a function to send daily Campaigns using SMTP**
   - **Implementation:** Integrated Django's SMTP backend inside `email_service.py`. Built a management command (`python manage.py send_daily_campaigns`) that filters campaigns matching today's date and initiates their dispatch. 
   - *Note: If SMTP credentials (`EMAIL_HOST_USER`, etc.) are omitted in the `.env` file, the app gracefully simulates success, making testing seamless.*

5. **Campaign Model Schema fields**
   - **Implementation:** Built the `Campaign` model to successfully hold the required fields: `subject`, `preview_text`, `article_url`, `html_content`, `plain_text_content`, and `published_date`.

6. **Render Email from a Base Template**
   - **Implementation:** Campaign emails are dynamically generated using Django's `render_to_string()` function. It injects the context variable into `campaigns/templates/base_email.html` ensuring a unified UI for every campaign sent.

---

## Architecture details: Optimization using Pub-Sub with Multiple Threads

To optimize sending time and ensure high performance, the campaign dispatcher completely offloads sequential synchronous SMTP connections to a parallel **Publisher-Subscriber (Pub-Sub)** messaging pattern running in memory.

**How this architecture operates (`dispatcher.py`):**

1. **Row-Level Db Locking (`select_for_update`)**: 
   When the dispatcher is called, it acquires a database lock on the `Campaign` row. This acts as a robust mutex, eliminating race conditions in environments with multiple cron-jobs triggering identical schedules.
   
2. **Bulk Preparation (Event creation)**: 
   The system quickly fetches all `is_active=True` subscribers and executes a `bulk_create` mapping all required emails as `PENDING` inside the `EmailLog` intermediate model.

3. **Publisher Thread (Producer)**: 
   A single background thread fetches pending `EmailLog` rows from the database and *publishes* them as individual jobs onto a shared thread-safe, unbounded `queue.Queue`.
   
4. **Subscriber Workers (Parallel Consumers)**: 
   - A concurrent pool of worker threads (`NUM_WORKER_THREADS = 10`) act as *Subscribers* to the queue. 
   - Operating in parallel, they continuously pull jobs from the queue, render the HTML template, negotiate the SMTP handshake, send the email (`EmailMultiAlternatives`), and update their assigned `EmailLog` status directly to `SENT` or `FAILED`.
   
5. **Sentinel Termination (Poison-Pill Shutdown)**: 
   Once the Publisher finishes sending the actual payload, it injects sentinel values (e.g., `None` poison-pills) onto the end of the queue. As worker threads ingest these pills, they gracefully terminate their loop.

6. **Conclusion**: 
   After all workers join, the overarching ThreadPool exits, and the `Campaign` is marked as `SENT`.

---

## Setup & Installation

**1. Clone the repository and navigate to the project directory:**
```bash
cd email_campaign_manager
```

**2. Create and activate a Virtual Environment:**
Using Conda:
```bash
conda create -n email_campaign_env python=3.11
conda activate email_campaign_env
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**4. Environment Variables:**
Copy `.env.example` to `.env` in the root directory and provide your SMTP credentials:

```bash
cp .env.example .env
```

**5. Apply Database Migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**6. Create an Admin User:**
```bash
python manage.py createsuperuser
```

**7. Run the Development Server:**
```bash
python manage.py runserver
```

## Running the Automated Dispatcher

You can run the built-in management command to send out any scheduled campaigns that are pending for today. Make sure your `.env` is properly populated with your Mailgun or Gmail app credentials!

```bash
python manage.py send_daily_campaigns
```

*In a production environment, this command should be bound to a daily Cron job or Celery Beat scheduler.*
```bash
0 0 * * * /your/venv/bin/python /your/project/manage.py send_daily_campaigns >> /var/log/email_dispatch.log 2>&1
```
