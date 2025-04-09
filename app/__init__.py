from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from flask import session

# Ініціалізація розширень
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # редірект якщо не авторизований

def create_app():
    app = Flask(__name__, template_folder=os.path.abspath('templates'))

    # 🔧 Конфігурація
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 🔌 Ініціалізація розширень
    db.init_app(app)
    login_manager.init_app(app)

    # 🔁 Імпорт маршрутів
    from app.routes import main
    app.register_blueprint(main)

    # 🧠 Імпортуємо моделі всередині функції, щоб уникнути циклічного імпорту
    from app.models import Customer, Contractor

    @login_manager.user_loader
    def load_user(user_id):
        role = session.get('role')
        if role == 'customer':
            return Customer.query.get(int(user_id))
        elif role == 'contractor':
            return Contractor.query.get(int(user_id))
        return None

    return app
