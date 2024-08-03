@echo off
REM Check if virtual environment exists
if not exist "env\Scripts\activate" (
    echo Creating virtual environment...
    python -m venv env
)

REM Activate virtual environment
call env\Scripts\activate

REM Install requirements
pip install -r requirements.txt

REM Check if database has been initialized
if not exist "instance\flaskr.sqlite" (
    echo Initializing database...
    python init_db.py
) else (
    echo Database already initialized.
)

REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

REM Run Flask application
flask run

echo Setup complete.
pause
