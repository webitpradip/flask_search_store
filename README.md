# Flask Search Store

A powerful Flask-based web application for managing and searching records with associated files. This application provides an intuitive interface for creating, editing, and searching through records while handling file attachments efficiently.

## Features

- **Record Management**
  - Create, edit, and delete records with titles, descriptions, and group names
  - Attach multiple files to each record
  - Organize records by groups

- **Advanced Search Functionality**
  - Full-text search across record titles and descriptions
  - Filter by group names
  - Search within specific date ranges
  - Results pagination

- **File Management**
  - Upload multiple files per record
  - Secure file storage
  - File deletion support

- **Data Import/Export**
  - Export database and files to ZIP archive
  - Import data from previously exported archives
  - UTF-8 support for international characters

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLAlchemy with SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Forms**: Flask-WTF
- **File Handling**: Werkzeug

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv env
   ```
3. Activate the virtual environment:
   - Windows: `env\Scripts\activate`
   - Unix/MacOS: `source env/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Initialize the database:
   ```bash
   python init_db.py
   ```

## Usage

1. Start the application:
   ```bash
   python app.py
   ```
   or use the provided `start.bat` script on Windows

2. Open your web browser and navigate to `http://localhost:5000`

3. Use the web interface to:
   - Create new records with files
   - Search existing records
   - Export/Import data
   - Manage files and records

## Project Structure

- `app.py`: Main application file with route handlers
- `models.py`: Database models for records and files
- `forms.py`: Form definitions using Flask-WTF
- `config.py`: Application configuration
- `templates/`: HTML templates
- `static/`: Static files (CSS, JavaScript)
- `uploads/`: File storage directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [MIT License](https://opensource.org/licenses/MIT) for details.
