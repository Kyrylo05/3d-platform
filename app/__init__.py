import os
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # Якщо не залогінений, редірект сюди

def file_exists_filter(path):
    return os.path.exists(os.path.join('app', 'static', path))

def create_app():
    app = Flask(__name__, template_folder=os.path.abspath('templates'))
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    

    # Щоб уникнути циклічного імпорту
    from app.models import Customer, Contractor
    from app.routes import main
    app.register_blueprint(main)

    @login_manager.user_loader
    def load_user(user_id):
        role = session.get('role')
        if role == 'customer':
            return Customer.query.get(int(user_id))
        elif role == 'contractor':
            return Contractor.query.get(int(user_id))
        return None

    # Створення папки для STL-файлів автоматично
    stl_upload_folder = os.path.join(app.root_path, 'static', 'uploads_stl')
    os.makedirs(stl_upload_folder, exist_ok=True)

    return app
