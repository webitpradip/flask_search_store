import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, abort
from werkzeug.utils import secure_filename
from forms import CreateForm
from models import db, Record, File
from config import Config
from datetime import datetime
import zipfile
from io import BytesIO
import sqlite3
from sqlalchemy import case, func, and_, desc


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.errorhandler(404)
def not_found_error(error):
    """
    Handle 404 Not Found errors.
    """
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server Error.
    """
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/create', methods=['GET', 'POST'])
def create():
    """
    Handle the creation of a new record.
    
    GET: Render the create form.
    POST: Process the submitted form, create a new record, and handle file uploads.
    """
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
    """
    List all records with pagination.
    """
    page = request.args.get('page', 1, type=int)
    records = Record.query.paginate(page, 10, False)
    next_url = url_for('list_records', page=records.next_num) if records.has_next else None
    prev_url = url_for('list_records', page=records.prev_num) if records.has_prev else None
    return render_template('list.html', records=records.items, next_url=next_url, prev_url=prev_url)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """
    Handle the editing of an existing record.
    
    GET: Render the edit form with existing record data.
    POST: Process the submitted form and update the record.
    """
    record = Record.query.get_or_404(id)
    form = CreateForm(obj=record)
    if form.validate_on_submit():
        record.title = form.title.data
        record.description = form.description.data
        record.group_name = form.group_name.data

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
    """
    Delete a file associated with a record.
    """
    file = File.query.get_or_404(id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        db.session.delete(file)
        db.session.commit()
        flash('File deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting file: {str(e)}', 'danger')
    return redirect(url_for('edit', id=file.record_id))

@app.route('/', methods=['GET', 'POST'])
def search():
    """
    Handle the advanced search functionality.
    
    GET: Render the search form and display results if query parameters are provided.
    POST: Process the search query and redirect to GET with query parameters.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if request.method == 'POST':
        return redirect(url_for('search', **request.form))

    query = request.args.get('query', '').strip()
    group_name = request.args.get('group_name', '').strip()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    filters = []

    if query:
        words = query.split()
        if len(words) > 10:
            flash('Please limit your search to 10 words or less.', 'warning')
            words = words[:10]
            query = ' '.join(words)
        
        filters.append(db.or_(
            Record.title.ilike(f'%{word}%') for word in words
        ) | db.or_(
            Record.description.ilike(f'%{word}%') for word in words
        ))

    if group_name:
        filters.append(Record.group_name.ilike(f'%{group_name}%'))

    if date_from:
        filters.append(Record.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))

    if date_to:
        filters.append(Record.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))

    if filters:
        # Create weight cases for relevance ranking
        title_cases = [case([(Record.title.ilike(f'%{word}%'), 3)], else_=0) for word in words] if query else []
        description_cases = [case([(Record.description.ilike(f'%{word}%'), 2)], else_=0) for word in words] if query else []
        group_name_cases = [case([(Record.group_name.ilike(f'%{group_name}%'), 1)], else_=0)] if group_name else []

        total_weight = sum(title_cases + description_cases + group_name_cases)

        results = Record.query.filter(and_(*filters)).add_columns(total_weight.label('weight')).order_by(desc(total_weight)).paginate(page, per_page, False)
    else:
        results = Record.query.add_columns(func.cast(0, db.Integer).label('weight')).paginate(page, per_page, False)

    # Remove 'page' from request.args to avoid duplicate 'page' parameter
    args = request.args.copy()
    args.pop('page', None)
    
    next_url = url_for('search', page=results.next_num, **args) if results.has_next else None
    prev_url = url_for('search', page=results.prev_num, **args) if results.has_prev else None

    return render_template('search.html', results=results.items, query=query, group_name=group_name, 
                           date_from=date_from, date_to=date_to, next_url=next_url, prev_url=prev_url)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """
    Serve uploaded files.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/export', methods=['GET', 'POST'])
def export():
    """
    Handle the export functionality.
    
    GET: Render the export form.
    POST: Process the export request and generate a zip file with the exported data.
    """
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
    """
    Export the database to a SQL file and add it to the zip file.
    """
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
    """
    Export all files in the upload folder to the zip file.
    """
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        for file in files:
            file_path = os.path.join(root, file)
            zf.write(file_path, os.path.relpath(file_path, app.config['UPLOAD_FOLDER']))

@app.route('/import', methods=['GET', 'POST'])
def import_data():
    """
    Handle the import functionality.
    
    GET: Render the import form.
    POST: Process the uploaded zip file and import the data.
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.zip'):
            try:
                with zipfile.ZipFile(file, 'r') as zf:
                    if 'database_export.sql' in zf.namelist():
                        import_database(zf)
                    for file_info in zf.infolist():
                        if file_info.filename != 'database_export.sql':
                            import_file(zf, file_info)
                flash('Data imported successfully!', 'success')
                return redirect(url_for('list_records'))
            except Exception as e:
                flash(f'Error importing data: {str(e)}', 'danger')
        else:
            flash('Invalid file format. Please upload a zip file.', 'danger')
    return render_template('import.html')

def import_database(zf):
    """
    Import the database from the SQL file in the zip file.
    """
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
    """
    Import a single file from the zip file to the upload folder.
    """
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info.filename)
    if not os.path.exists(file_path):
        zf.extract(file_info.filename, app.config['UPLOAD_FOLDER'])

@app.context_processor
def inject_now():
    """
    Inject the current year into all templates.
    """
    return {'current_year': datetime.utcnow().year}

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
