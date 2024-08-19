import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory
from werkzeug.utils import secure_filename
from forms import CreateForm
from models import db, Record, File
from config import Config
from datetime import datetime
import zipfile
from io import BytesIO
import sqlite3

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.route('/create', methods=['GET', 'POST'])
def create():
    form = CreateForm()
    if form.validate_on_submit():
        record = Record(title=form.title.data, description=form.description.data, group_name=form.group_name.data)
        db.session.add(record)
        db.session.commit()

        files = request.files.getlist('files')
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                db_file = File(filename=filename, record_id=record.id)
                db.session.add(db_file)

        db.session.commit()
        flash('Record created successfully!', 'success')
        return redirect(url_for('list_records'))
    return render_template('create.html', form=form)

@app.route('/list')
def list_records():
    page = request.args.get('page', 1, type=int)
    records = Record.query.paginate(page, 10, False)
    next_url = url_for('list_records', page=records.next_num) if records.has_next else None
    prev_url = url_for('list_records', page=records.prev_num) if records.has_prev else None
    return render_template('list.html', records=records.items, next_url=next_url, prev_url=prev_url)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    record = Record.query.get_or_404(id)
    form = CreateForm(obj=record)
    if form.validate_on_submit():
        # Populate other fields
        record.title = form.title.data
        record.description = form.description.data
        record.group_name = form.group_name.data

        # Handle file uploads if any
        files = request.files.getlist('files')
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                db_file = File(filename=filename, record_id=record.id)
                db.session.add(db_file)

        db.session.commit()
        flash('Record updated successfully!', 'success')
        return redirect(url_for('list_records'))
    return render_template('edit.html', form=form, record=record)

@app.route('/delete_file/<int:id>')
def delete_file(id):
    file = File.query.get_or_404(id)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    db.session.delete(file)
    db.session.commit()
    flash('File deleted successfully!', 'success')
    return redirect(url_for('edit', id=file.record_id))

@app.route('/', methods=['GET', 'POST'])
def search():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    query = request.form.get('query', '')

    if request.method == 'POST':
        return redirect(url_for('search', query=query))

    if query:
        words = query.split()
        filters = []
        for word in words:
            word_filter = (
                Record.title.contains(word) |
                Record.description.contains(word) |
                Record.group_name.contains(word)
            )
            filters.append(word_filter)

        results = Record.query.filter(db.or_(*filters)).paginate(page, per_page, False)
    else:
        results = Record.query.paginate(page, per_page, False)

    next_url = url_for('search', query=query, page=results.next_num) if results.has_next else None
    prev_url = url_for('search', query=query, page=results.prev_num) if results.has_prev else None

    return render_template('search.html', results=results.items, query=query, next_url=next_url, prev_url=prev_url)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/export', methods=['GET', 'POST'])
def export():
    if request.method == 'POST':
        export_type = request.form.get('export_type')
        
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            if export_type in ['database', 'both']:
                export_database(zf)
            if export_type in ['files', 'both']:
                export_files(zf)
        memory_file.seek(0)
        
        return send_file(memory_file, attachment_filename='export.zip', as_attachment=True)
    return render_template('export.html')

def export_database(zf):
    db_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database_export.sql')
    conn = db.engine.raw_connection()
    try:
        with open(db_file_path, 'w') as f:
            for line in conn.iterdump():
                f.write('%s\n' % line)
        zf.write(db_file_path, 'database_export.sql')
    finally:
        conn.close()
        os.remove(db_file_path)

def export_files(zf):
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        for file in files:
            file_path = os.path.join(root, file)
            zf.write(file_path, os.path.relpath(file_path, app.config['UPLOAD_FOLDER']))

@app.route('/import', methods=['GET', 'POST'])
def import_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file:
            with zipfile.ZipFile(file, 'r') as zf:
                if 'database_export.sql' in zf.namelist():
                    import_database(zf)
                for file_info in zf.infolist():
                    if file_info.filename != 'database_export.sql':
                        import_file(zf, file_info)
            flash('Data imported successfully!', 'success')
            return redirect(url_for('list_records'))
    return render_template('import.html')

def import_database(zf):
    db_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database_import.sql')
    with open(db_file_path, 'wb') as f:
        f.write(zf.read('database_export.sql'))
    
    with open(db_file_path, 'r') as f:
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        buffer = ""
        for line in f:
            buffer += line.strip()
            if line.strip().endswith(";"):  # Execute when the line ends with a semicolon
                try:
                    cursor.execute(buffer)
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint failed" in str(e):
                        # Handle unique constraint failure
                        print(f"Skipping duplicate record: {e}")
                    else:
                        raise
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e):
                        # Handle already exists error
                        print(f"Skipping existing table or record: {e}")
                    else:
                        raise
                buffer = ""
        conn.commit()
    os.remove(db_file_path)

def import_file(zf, file_info):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info.filename)
    if not os.path.exists(file_path):
        zf.extract(file_info.filename, app.config['UPLOAD_FOLDER'])

@app.context_processor
def inject_now():
    return {'current_year': datetime.utcnow().year}

if __name__ == '__main__':
    app.run(debug=True)
