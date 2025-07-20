import os
import io
import csv
from openpyxl import load_workbook
from weasyprint import HTML
from dotenv import load_dotenv

from flask import send_file, Response, request, redirect, url_for, flash
from flask import Flask, render_template, make_response
from werkzeug.utils import secure_filename
import pandas as pd
from schedule import TeacherSchedule
from utils import get_file, allowed_file, create_folder, style_excel_output, set_alternating_column_background

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
    data["agsstd"] = meta.get("Ags-Std", 0)
    data['ags'] = meta.get("Ags-AG", '')
    data["poolstd"] = meta.get("Poolstd-Std", 0)
    data['pool'] = meta.get("Poolstd-Bg", '')

    return render_template("teacher_load.html", data=data)


@app.route("/teacher/load/export/excel")
def export_teacher_load_excel():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name in ts.get_df().index:
            data = ts.compare_load(name)
            meta = ts.get_teaching_load(name)

            # Build export data
            meta_data = {
                "Deputat": meta.get("Deputat 24/25", 0),
                "Anr": meta.get("Anr", 0),
                "Bonus": meta.get("Bonus", 0),
                "Sonderaufgaben": meta.get("Sonderaufgaben", ''),
                "Ags-Std": meta.get("Ags-Std", 0),
                "Ags-AG": meta.get("Ags-AG", ''),
                "Poolstd-Std": meta.get("Poolstd-Std", 0),
                "Poolstd-Bg": meta.get("Poolstd-Bg", ''),
                "Deputat (net)": data.get('expected', 0),
                "WS": data.get('assigned', 0),
                "Bonus (Zukunft)": data.get('delta', 0),
            }
            
            # Transpose meta data
            result_df = pd.DataFrame.from_dict(meta_data, orient='index', columns=['Stunden'])
            result_df = result_df.reset_index().rename(columns={"index": "Aufgabe"})

            # move Sonderaufgaben, Ags-Std and Poolstd-Std to a separate column
            def get_description(row):
                if row["Aufgabe"] == "Anr":
                    return meta_data.get("Sonderaufgaben", "")
                elif row["Aufgabe"] == "Ags-Std":
                    return meta_data.get("Ags-AG", "")
                elif row["Aufgabe"] == "Poolstd-Std":
                    return meta_data.get("Poolstd-Bg", "")
                return ""

            result_df["Beschreibung"] = result_df.apply(get_description, axis=1)
            rows_to_remove = ["Sonderaufgaben", "Ags-AG", "Poolstd-Bg"]
            result_df = result_df[~result_df["Aufgabe"].isin(rows_to_remove)]

            # Combine meta + load
            # result_df = pd.concat([meta_df, pd.DataFrame([df])], axis=1)
            # result_df =  meta_df.T.reset_index()
            # result_df.columns = ["Aufgabe", "Stunden"]
            sheet_name = name
            result_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # max Excel sheet name length is 31
            ws = writer.sheets[sheet_name]
            ws = style_excel_output(writer.book, sheet_name, result_df.columns.tolist(), highlight_cell={'row': 'Bonus (Zukunft)', 'column': 'Stunden'})
            


    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="teachers_loads.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



@app.route("/dashboard")
def dashboard():
    rows = ts.get_dashboard_rows()
    return render_template("dashboard.html", rows=rows)


@app.route("/export/dashboard/csv")
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
        "Ags-Std",
        "Poolstd-Std",
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
                row.get("ags", ""),
                row.get("pool", ""),
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

@app.route("/export/dashboard/excel")
def export_dashboard_excel():
    teacher_names = ts.get_df().index.tolist()
    rows = []

    for name in teacher_names:
        load = ts.compare_load(name)
        meta = ts.get_teaching_load(name)
        load["Lehrer*in"] = name
        load["Deputat"] = meta.get("Deputat 24/25", 0)
        load["Anr"] = meta.get("Anr", 0)
        load["Bonus"] = meta.get("Bonus", 0)
        load["Ags"] = meta.get("Ags-Std", 0)
        load["Poolstd"] = meta.get("Poolstd-Std", 0)
        load["Sonderaufgaben"] = meta.get("Sonderaufgaben", "")
        rows.append(load)

    df_export = pd.DataFrame(rows)

    # Optional: specify column order
    columns = [
        "Lehrer*in", "Deputat", "Anr", "Bonus", "Ags", "Poolstd", "Sonderaufgaben",
        "expected", "assigned", "delta"
    ]
    df_export = df_export[columns]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name="Dashboard")

    output.seek(0)

    wb = load_workbook(output)
    wb = style_excel_output(wb, "Dashboard", columns, highlight_column='delta')

    styled_output = io.BytesIO()
    wb.save(styled_output)
    styled_output.seek(0)

    return send_file(
        styled_output,
        download_name="dashboard.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
    sort = request.args.get("sort", "teacher") 
    print("sort:", sort)
    df_list = ts.build_wide_class_table(sort)
    if request.headers.get("HX-Request"):
        print("HX-Request")
        return render_template("partials/_class_summary_table.html", table_list=df_list, sort=sort)
    return render_template("class_summary.html", table_list=df_list, sort=sort)


@app.route("/summary/export/", defaults={'sort': 'teacher'})
@app.route("/summary/export/<sort>")
def export_summary_csv(sort):
    df = ts.build_wide_class_table(sort)
    csv_data = io.StringIO()
    df.to_csv(csv_data, index=False)
    csv_data.seek(0)
    return send_file(
        io.BytesIO(csv_data.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="teacher_class_summary.csv",
    )

from flask import send_file
import io

@app.route("/summary/export/excel")
def export_summary_excel():
    sort = 'teacher'
    tables_by_grade = ts.build_wide_class_table(sort)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table in tables_by_grade:
            grade = table['grade']
            df = table['df']
            sheet_name=f"Stufe {grade}"
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.book[sheet_name]
            style_excel_output(writer.book, sheet_name, df.columns.tolist())
            set_alternating_column_background(ws, start_row=2, step=3)

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="class_tables.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/summary/export/pdf")
def export_summary_pdf():
    sort = 'teacher'
    grade_tables = ts.build_wide_class_table(sort)  # list of {'grade': '5', 'df': DataFrame}

    rendered = render_template("pdf_export.html", grade_tables=grade_tables)
    pdf_file = io.BytesIO()
    HTML(string=rendered).write_pdf(pdf_file)

    pdf_file.seek(0)
    response = make_response(pdf_file.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=alle_klassenstufen.pdf"
    return response

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
    app.run()
