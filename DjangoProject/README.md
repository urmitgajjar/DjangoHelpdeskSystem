# Django HelpDesk Ticket Management System 🎫

A full-stack **ticket management system** built using **Django**, designed to handle internal support tickets with role-based access, analytics, and background ticket processing.

This project focuses on clean backend architecture, real-world workflows, and maintainable code practices.

---

## 🚀 Features

- User & Superuser role-based access
- Ticket creation, update, assignment, and resolution flow
- Ticket history and activity logs
- Analytics dashboard (status distribution, trends)
- Notification system
- Background tickets using Celery
- Clean UI using Django Templates (HTML + inline CSS)

---

## 🛠 Tech Stack

- **Backend:** Django (Python)
- **Frontend:** HTML, CSS (inline)
- **Database:** SQLite (development)
- **Async Tickets:** Celery
- **Version Control:** Git & GitHub

---

## 📂 Project Structure

```text
HelpDesk/
├── HelpDesk/          # Project settings
├── myapp/             # Core application (tickets, users, analytics)
├── manage.py
├── .gitignore
└── README.md