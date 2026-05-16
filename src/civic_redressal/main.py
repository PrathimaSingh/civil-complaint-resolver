# civic_redressal/main.py
from civic_redressal.web.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)