import os
import io
import csv
from flask import send_file, Response, request, redirect, url_for, flash
from flask import Flask, render_template
from werkzeug.utils import secure_filename
import pandas as pd
from schedule import TeacherSchedule

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

ts = None


DEFAULT_EXCEL_PATH = os.getenv("DEFAULT_EXCEL_PATH")
UPLOAD_FOLDER = "data"
ALLOWED_EXTENSIONS = {"xls", "xlsx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def init_teacher_schedule(filepath=None):
    if filepath and os.path.exists(filepath):
        ts = TeacherSchedule(filepath)
    elif DEFAULT_EXCEL_PATH and os.path.exists(DEFAULT_EXCEL_PATH):
        ts = TeacherSchedule(DEFAULT_EXCEL_PATH)
    else:
        ts = None
        print("⚠️ No valid Excel file found.")
    return ts


# init TeacherSchedule instance
ts = init_teacher_schedule()


@app.route("/")
def index():
    if not ts:
        flash("No valid Excel file loaded. Please upload one.", "warning")
        return redirect(url_for("upload_file"))
    class_names = ts.get_classes()
    teacher_names = ts.get_df().index.tolist()
    return render_template("index.html", classes=class_names, teachers=teacher_names)


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files.get("file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            init_teacher_schedule(filepath)
            flash("Upload successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid file type. Please upload an Excel file.", "danger")
            return redirect(url_for("upload_file"))

    return render_template("upload.html")


@app.route("/class/<cls>")
def show_class(cls):
    records = ts.get_teachers_in_class(cls)
    return render_template("class.html", class_name=cls, table=records)


@app.route("/teacher/<name>")
def show_teacher(name):
    records = ts.get_classes_of_teacher(name)
    total = ts.get_total_lessons(name)
    load = ts.get_teaching_load(name)
    compare = ts.compare_load(name)
    return render_template(
        "teacher.html",
        teacher_name=name,
        table=records,
        total=total,
        load=load,
        compare=compare,
    )


@app.route("/teacher/<name>/load")
def show_teacher_load(name):
    data = ts.compare_load(name)

    # Optional: enrich with anr and bonus separately
    meta = ts.get_teaching_load(name)
    data["anr"] = meta.get("Anr", 0)
    data["bonus"] = meta.get("Bonus", 0)

    return render_template("teacher_load.html", data=data)


@app.route("/dashboard")
def dashboard():
    rows = ts.get_dashboard_rows()
    return render_template("dashboard.html", rows=rows)


@app.route("/export/dashboard")
def export_dashboard_csv():
    rows = ts.get_dashboard_rows()
    if not rows:
        return "No data to export", 400

    column_order = ["teacher", "dep", "anr", "bonus", "expected", "assigned", "delta"]
    column_labels = [
        "Lehrer*in",
        "Deputat",
        "Anr",
        "Bonus",
        "Deputat (net)",
        "WS",
        "Delta",
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(column_labels)
    for row in rows:
        writer.writerow(
            [
                row.get("teacher", ""),
                row.get("dep", ""),
                row.get("anr", ""),
                row.get("bonus", ""),
                row.get("expected", ""),
                row.get("assigned", ""),
                row.get("delta", ""),
            ]
        )
    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=teacher_dashboard.csv"},
    )


@app.route("/export/class/<cls>.csv")
def export_class_csv(cls):
    df = ts.get_df(reset_index=True)
    subset = ts.get_teachers_in_class(cls)
    if not subset:
        return "No data", 404

    export_df = pd.DataFrame(subset)
    output = io.StringIO()
    export_df.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        download_name=f"{cls}.csv",
        as_attachment=True,
    )


@app.route("/export/teacher/<name>.csv")
def export_teacher_csv(name):
    subset = ts.get_classes_of_teacher(name)
    if not subset:
        return "No data", 404

    export_df = pd.DataFrame(subset)
    output = io.StringIO()
    export_df.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        download_name=f"{name}.csv",
        as_attachment=True,
    )


@app.route("/summary")
def class_summary():
    df = ts.build_wide_class_table()
    return render_template("class_summary.html", table=df)


@app.route("/summary/export")
def export_summary_csv():
    df = ts.build_wide_class_table()
    csv_data = io.StringIO()
    df.to_csv(csv_data, index=False)
    csv_data.seek(0)
    return send_file(
        io.BytesIO(csv_data.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="teacher_class_summary.csv",
    )


if __name__ == "__main__":
    app.run(debug=True)
