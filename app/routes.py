from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Customer, Contractor, Offer, Order

main = Blueprint('main', __name__)

# ------------------ Головна ------------------
@main.route('/')
def home():
    return render_template('index.html')


# ------------------ Універсальна реєстрація ------------------
@main.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if role not in ['customer', 'contractor']:
        return "Невідома роль", 404

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if password != confirm:
            return "Паролі не співпадають!"

        model = Customer if role == 'customer' else Contractor
        existing = model.query.filter_by(email=email).first()
        if existing:
            return "Email вже використовується!"

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        if role == 'customer':
            new_user = Customer(full_name=name, email=email, password=hashed_password)
        else:
            new_user = Contractor(company_name=name, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('main.login', role=role))

    return render_template('register.html', role=role)


# ------------------ Універсальний вхід ------------------
@main.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if role not in ['customer', 'contractor']:
        return "Невідома роль", 404

    model = Customer if role == 'customer' else Contractor

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = model.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            return "Невірний email або пароль!"

        session['role'] = role  # Зберігаємо роль у сесії
        login_user(user)

        if role == 'contractor':
            return redirect(url_for('main.dashboard', role='contractor'))
        else:
            return redirect(url_for('main.view_offers'))

    return render_template('login.html', role=role)


# ------------------ Універсальний кабінет ------------------
@main.route('/dashboard/<role>')
@login_required
def dashboard(role):
    if role == 'contractor':
        offers = Offer.query.filter_by(contractor_id=current_user.id).all()
        return render_template('dashboard.html', user=current_user, role=role, offers=offers)
    elif role == 'customer':
        return redirect(url_for('main.view_offers'))
    else:
        return "Невідома роль", 404


# ------------------ Вихід ------------------
@main.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('role', None)
    return redirect(url_for('main.home'))


# ------------------ Створення пропозиції ------------------
@main.route('/contractor/create_offer', methods=['GET', 'POST'])
@login_required
def create_offer():
    if session.get('role') != 'contractor':
        return "Доступ лише для друкарів", 403

    if request.method == 'POST':
        material = request.form['material']
        layer_height = float(request.form['layer_height'])
        price_per_gram = float(request.form['price_per_gram'])
        max_size = request.form['max_size']
        min_size = request.form['min_size']

        offer = Offer(
            material=material,
            layer_height=layer_height,
            price_per_gram=price_per_gram,
            max_size=max_size,
            min_size=min_size,
            contractor_id=current_user.id
        )
        db.session.add(offer)
        db.session.commit()

        return redirect(url_for('main.dashboard', role='contractor'))

    return render_template('create_offer.html')


# ------------------ Перегляд пропозицій (замовником) ------------------
@main.route('/offers')
@login_required
def view_offers():
    if session.get('role') != 'customer':
        return "Доступ лише для замовників", 403

    offers = Offer.query.all()
    return render_template('offers_list.html', offers=offers)
