# Cloud-Based Library Management System

A web application to manage books, students, and book issue/return transactions.

## Tech Stack
- Frontend: HTML, CSS, JavaScript, Bootstrap
- Backend: Python, Flask
- Database: PostgreSQL on Supabase
- Deployment: Render

## Features
- Admin login and logout
- Dashboard with live statistics
- Book management with search
- Student management
- Issue and return with automatic availability updates
- Full transaction history with filters

## Run locally
1. Create a virtual environment and install dependencies:
   `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your own values.
3. Create the tables: `flask --app app init-db`
4. Create an admin: `python create_admin.py`
5. Start the app: `python app.py`