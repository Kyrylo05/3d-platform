from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder='../templates')
    
    # Налаштування
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Підключаємо базу та логін
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'  # куди перенаправити, якщо не залогінений

    # Імпорт маршрутів
    from app.routes import main
    app.register_blueprint(main)

    # Імпорт моделі та функція завантаження користувача
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
