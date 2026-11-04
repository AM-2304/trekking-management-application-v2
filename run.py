"""Flask entry point.

    python run.py                       # start the development server
    flask --app run.py seed             # create and populate the database
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
