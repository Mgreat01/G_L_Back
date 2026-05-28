# 🧠 FastAPI Backend Project

This project is a comprehensive FastAPI backend application that provides a robust and scalable framework for building web services. It includes features such as user authentication, authorization, and geospatial functionality, making it an ideal starting point for a wide range of applications. The project is designed to be highly customizable and extensible, allowing developers to easily add new features and functionality as needed.

---

## 🚀 Features

* User authentication and authorization using JSON Web Tokens (JWT)
* Geospatial functionality using GeoAlchemy2 and Shapely
* Support for multiple database engines using SQLAlchemy
* CORS middleware for cross-origin requests
* Automatic API documentation using FastAPI's built-in support for Swagger UI
* Robust error handling and logging mechanisms
* Highly customizable and extensible architecture

---

## 🛠️ Tech Stack

* **FastAPI** — Modern high-performance Python API framework
* **SQLAlchemy** — ORM and SQL toolkit
* **GeoAlchemy2** — Geospatial support for SQLAlchemy
* **Shapely** — Geometric object manipulation and analysis
* **Passlib** — Password hashing
* **Python-Jose** — JWT token management
* **Pydantic** — Validation and settings management
* **Dotenv** — Environment variable loader
* **PostgreSQL + PostGIS** — Spatial database support

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Mgreat01/G_L_Back.git
cd G_L_Back
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# ⚙️ Environment Variables (.env)

The application uses a `.env` file to store sensitive configuration values such as database credentials, JWT secrets, and API settings.

Create a `.env` file at the root of the project:

```bash
touch .env
```

Or manually create a file named:

```text
.env
```

---

## 🧩 Example `.env` Configuration

```env
# ==========================================
# DATABASE CONFIGURATION
# ==========================================
DATABASE_URL=postgresql://postgres:password@localhost:5432/g_l_back

# ==========================================
# JWT / SECURITY
# ==========================================
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ==========================================
# APPLICATION SETTINGS
# ==========================================
DEBUG=True
APP_NAME=FastAPI Backend Project

# ==========================================
# SERVER CONFIGURATION
# ==========================================
HOST=0.0.0.0
PORT=8000
```

---

## 📘 Explanation of Each Variable

| Variable                      | Description                            |
| ----------------------------- | -------------------------------------- |
| `DATABASE_URL`                | Connection URL for PostgreSQL database |
| `SECRET_KEY`                  | Secret key used to sign JWT tokens     |
| `ALGORITHM`                   | JWT encryption algorithm               |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time in minutes       |
| `DEBUG`                       | Enables debug mode                     |
| `APP_NAME`                    | Application name                       |
| `HOST`                        | API server host                        |
| `PORT`                        | API server port                        |

---

## 🗄️ PostgreSQL + PostGIS Setup

This project uses PostgreSQL with PostGIS extension for geospatial features.

### Install PostgreSQL

Download PostgreSQL:

* Windows/macOS/Linux:

  * [https://www.postgresql.org/download/](https://www.postgresql.org/download/)

### Enable PostGIS Extension

After creating your database, connect to PostgreSQL and run:

```sql
CREATE EXTENSION postgis;
```

---

## 🧪 Example Database Creation

```sql
CREATE DATABASE g_l_back;
```

Then connect to the database:

```sql
\c g_l_back
```

Enable PostGIS:

```sql
CREATE EXTENSION postgis;
```

---

## ▶️ Running the Application

Run the FastAPI server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python main.py
```

---

## 📚 API Documentation

Once the server is running:

| Documentation | URL                                                        |
| ------------- | ---------------------------------------------------------- |
| Swagger UI    | [http://localhost:8000/docs](http://localhost:8000/docs)   |
| ReDoc         | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

---

## 📂 Project Structure

```text
.
├── backend
│   ├── app
│   │   ├── core
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   ├── main.py
│   │   ├── models
│   │   ├── routes
│   │   ├── services
│   │   ├── utils
│   │   │   ├── geo_utils.py
│   │   │   ├── gps.py
│   ├── requirements.txt
├── main.py
├── README.md
```

---

## 🔐 Security Recommendations

For production environments:

* Use a strong `SECRET_KEY`
* Disable `DEBUG`
* Use HTTPS
* Store secrets securely
* Restrict database access
* Use environment-specific `.env` files

---

## 🤝 Contributing

To contribute to the project:

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Push your branch
5. Open a Pull Request

---

