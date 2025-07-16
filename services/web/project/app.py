import os
import io
import csv
from dotenv import load_dotenv

from flask import send_file, Response, request, redirect, url_for, flash
from flask import Flask, render_template
from werkzeug.utils import secure_filename
import pandas as pd
from project.schedule import TeacherSchedule
from project.utils import get_file, allowed_file, create_folder

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

project_path = os.path.dirname(os.path.realpath(__file__))
print(f"Project path: {project_path}")
print(f"UPLOAD_FOLDER: {os.getenv('UPLOAD_FOLDER')}")

upload_folder = os.path.join(project_path, os.getenv("UPLOAD_FOLDER"))
app.config["UPLOAD_FOLDER"] = upload_folder

ALLOWED_EXTENSIONS = {"xls", "xlsx"}

create_folder(upload_folder)

excel_file = get_file(upload_folder, ALLOWED_EXTENSIONS)
print(f"Excel file: {excel_file}")

if excel_file:
    ts = TeacherSchedule(excel_file)
    print(f"Loaded Excel from: {excel_file}")
else:
    ts = None
    print("⚠️ No Excel file found. Waiting for upload.")


@app.route("/")
def index():
    global ts
    if not ts:
        flash("No valid Excel file loaded. Please upload one.", "warning")
        return redirect(url_for("upload_file"))
    class_names = ts.get_classes()
    teacher_names = ts.get_df().index.tolist()
    return render_template("index.html", classes=class_names, teachers=teacher_names)


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    global ts
    if request.method == "POST":
        file = request.files.get("file")
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            ts = TeacherSchedule(filepath)
            flash("Upload successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid file type. Please upload an Excel file.", "danger")
            return redirect(url_for("upload_file"))

    return render_template("upload.html")


@app.route("/class/<cls>")
def show_class(cls):
    records = ts.get_teachers_in_class(cls)
    main_teachers_for_class = ts.class_teachers.get(cls, {})
    main_teacher = main_teachers_for_class.get("main")
    deputies = main_teachers_for_class.get("deputies", [])
    return render_template(
        "class.html", 
        class_name=cls, 
        table=records,
        main_teacher=main_teacher,
        deputies=deputies,
    )


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
    data["dep"] = meta.get("Deputat 24/25", 0)
    data["anr"] = meta.get("Anr", 0)
    data["bonus"] = meta.get("Bonus", 0)
    data["sonderaufgaben"] = meta.get("Sonderaufgaben", '')

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

@app.route("/export/schedule.csv")
def export_schedule_csv():
    long_df = ts.get_teacher_schedule_long()  # Your method to get long format DataFrame

    # Convert DataFrame to CSV string
    csv_buffer = io.StringIO()
    long_df.to_csv(csv_buffer, index=False)

    # Create a Flask Response with CSV
    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=teacher_schedule.csv"}
    )


if __name__ == "__main__":
    app.run(debug=True)
