# 📘 Teacher Schedule Dashboard

A Flask web app to visualize, filter, and analyze teaching schedules and workloads from a multi-index Excel file.


## 🚀 Features

- 📥 Upload Excel file with teacher/class schedule data
- 📊 Dashboard view for teaching load comparison
- 🏫 Class-specific views with subject + lesson assignments
- 👤 Teacher-specific overview
- 📤 Export to CSV
- 📁 Default Excel fallback via `.env`
- 🧼 Handles malformed data (non-teacher rows, extra columns)
- 🎨 Responsive Bootstrap layout


## ⚙️ Setup

1. **Install dependencies**


```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```
flask
pandas
openpyxl
python-dotenv
```
### ⚡ Using `uv` (Optional)

This project supports [`uv`](https://github.com/astral-sh/uv), a super-fast Python package manager:

### 🚀 Why use `uv`?

- ✅ Blazing fast installs (Rust-powered)
- ✅ No need for virtualenv
- ✅ Compatible with `pyproject.toml`
- ✅ Easy to keep reproducible environments

### 🔧 Installing dependencies with `uv`

If you're using `uv`, you can install everything from `pyproject.toml`:

```bash
uv pip install -r pyproject.toml
```

To generate a `requirements.txt` for compatibility:

```bash
uv pip freeze > requirements.txt
```

2. **Create `.env` file**

```ini
DEFAULT_EXCEL_PATH=uploads/default_schedule.xlsx
```

3. **Run the app**

```bash
python app.py
```

Or with `flask run`:

```bash
export FLASK_APP=app.py
flask run
```

---

## 📄 Excel File Format

- **Two-row header**: e.g., `("5a", "Fach")`, `("5a", "Stunden")`
- Empty columns or duplicated name columns are ignored
- Teaching load: columns like `'Deputat 24/25'`, `'Anr'`, `'Bonus'`
- Rows starting from 5 (teachers listed as `Last, First`)

---

## 📤 Uploading a File

Go to `/upload` to submit a new Excel file.
If no file is uploaded, the app will use the one from `.env`.

---

## 🧪 Example Use Cases

- Compare teaching load with assigned lessons
- Export filtered views for class schedules
- Identify over- or under-loaded teachers
- Build printable reports or CSV files

---

## 💡 Ideas for Future Enhancements

- Export to PDF
- Role-based user authentication
- Admin interface for managing data
- Data persistence in database

---

## 🛡 License

MIT — use freely, but attribution appreciated.
