# 🎫 AI-Powered HelpDesk Management System

An intelligent HelpDesk Ticket Management System built using **Django**, **Machine Learning**, and **AI-based automation** for efficient ticket handling, smart department routing, and automated priority prediction.

---

## ✨ Features

- 🔐 User and Admin Authentication
- 🖥️ Separate User and Admin Portals
- 🤖 AI-Based Ticket Priority Prediction
- 🧠 Machine Learning Department Prediction
- 📧 Email Notification System
- 🛡️ Role-Based Access Control
- 🎟️ Ticket Status Management
- 🔔 Notification Management System
- 📱 Responsive Dashboard UI
- 🔒 Secure Environment Variable Configuration
- 🗄️ SQLite Support (Development)
- 🐘 PostgreSQL Ready (Production)

---

## 🛠️ Tech Stack

### Backend
- Python
- Django

### Database
- SQLite *(Current Development Database)*
- PostgreSQL *(Production Ready)*

### Machine Learning / AI
- Scikit-learn
- TF-IDF Vectorization
- Logistic Regression
- Groq API Integration

### Frontend
- HTML
- CSS
- Bootstrap
- JavaScript

---

## 📁 Project Structure

```text
DjangoHelpdeskProject/
│
├── HelpDesk/
├── myapp/
├── static/
├── media/
├── logs/
├── templates/
├── manage.py
├── requirements.txt
├── README.md
└── .env (ignored)
```

---

## 🚀 Installation and Setup

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/django-helpdesk-system.git
```

### 2. Navigate to Project Folder

```bash
cd django-helpdesk-system
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Virtual Environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Variables

Create a `.env` file in the project root and configure the following variables and for more details, refer to the file called .env.example for more idea:

```env
# Django Core Settings
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com

# GROQ AI Configuration
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## 🗃️ Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 👤 Create Superuser

```bash
python manage.py createsuperuser
```

---

## ▶️ Run Development Server

```bash
python manage.py runserver
```

Open browser: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

Admin Panel: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🤖 AI Features

### AI Priority Prediction
Automatically predicts ticket priority using AI integration (Groq API with LLaMA model), reducing manual effort and ensuring urgent tickets are handled first.

### ML Department Prediction
Uses Machine Learning (TF-IDF + Logistic Regression) to automatically assign departments based on ticket title and description, enabling faster routing and resolution.

---

## 🔐 Security Features

- ✅ Environment Variable Protection
- ✅ CSRF Protection
- ✅ Session Security
- ✅ Role-Based Authentication
- ✅ Secure Email Configuration

---

## 🔮 Future Enhancements

- [ ] PostgreSQL Production Deployment
- [ ] Docker Support
- [ ] REST API Integration
- [ ] Real-time Notifications
- [ ] Analytics Dashboard
- [ ] File Attachment Support
- [ ] Cloud Deployment

---

## 👨‍💻 Author

**Urmit Gajjar**
B.Tech Computer Engineering Student

---

## 📄 License

This project is developed for **educational and portfolio purposes**.
