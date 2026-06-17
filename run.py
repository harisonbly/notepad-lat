import os
from app import create_app, celery
from dotenv import load_dotenv

load_dotenv()
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=app.debug)
