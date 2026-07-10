import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from models.database import init_db

app = create_app()

if __name__ == '__main__':
    print(f"Database: {os.environ.get('DB_TYPE', 'sqlite')}")
    app.run(debug=True, port=5000)
