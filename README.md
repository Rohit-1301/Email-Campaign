# Email Campaign Manager

A production-ready Email Campaign Manager built with Django and Django REST Framework.

## Features
- Relational model design with many-to-many intermediate models
- ThreadPoolExecutor for multithreaded email dispatching
- Row-level locking and race condition prevention
- Clean service-layer architecture
- Admin usability optimized
- SMTP integration included

## Setup

1. Environment setup:
```bash
conda create -n email_campaign_env python=3.11
conda activate email_campaign_env
pip install -r requirements.txt
```

2. Run Migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create Superuser:
```bash
python manage.py createsuperuser
```

4. Run the Development Server:
```bash
python manage.py runserver
```

## Daily Automation
Use the following command to send daily campaigns scheduled for today:
```bash
python manage.py send_daily_campaigns
```
