from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from app.models import db, Customer, Contractor, Offer, Order

main = Blueprint('main', __name__)


# ------------------ Головна ------------------
@main.route('/')
def home():
    return render_template('index.html')


# ------------------ Реєстрація ------------------
@main.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if role not in ['customer', 'contractor']:
        return "Невідома роль", 404

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        file = request.files.get('profile_image')

        if password != confirm:
            return "Паролі не співпадають!"

        model = Customer if role == 'customer' else Contractor
        existing = model.query.filter_by(email=email).first()
        if existing:
            return "Email вже використовується!"

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        filename = 'default-avatar.png'

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            save_path = os.path.join('app', 'static', 'uploads', filename)
            file.save(save_path)

        new_user = Customer(full_name=name, email=email, password=hashed_password, profile_image=filename) if role == 'customer' else \
                   Contractor(company_name=name, email=email, password=hashed_password, profile_image=filename)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('main.login', role=role))

    return render_template('register.html', role=role)


# ------------------ Вхід ------------------
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

        session['role'] = role
        login_user(user)

        return redirect(url_for('main.dashboard', role=role))

    return render_template('login.html', role=role)


# ------------------ Кабінет ------------------
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

        files = request.files.getlist('images')
        examples_path = os.path.join('app', 'static', 'examples')
        os.makedirs(examples_path, exist_ok=True)

        for idx, file in enumerate(files[:3]):
            if file and file.filename != '':
                filename = f'offer_{offer.id}_example_{idx+1}.jpg'
                file.save(os.path.join(examples_path, filename))

        return redirect(url_for('main.dashboard', role='contractor'))

    return render_template('create_offer.html')


# ------------------ Редагування пропозиції ------------------
@main.route('/contractor/edit_offer/<int:offer_id>', methods=['GET', 'POST'])
@login_required
def edit_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    if offer.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    if request.method == 'POST':
        offer.material = request.form['material']
        offer.layer_height = float(request.form['layer_height'])
        offer.price_per_gram = float(request.form['price_per_gram'])
        offer.max_size = request.form['max_size']
        offer.min_size = request.form['min_size']

        db.session.commit()
        return redirect(url_for('main.dashboard', role='contractor'))

    return render_template('edit_offer.html', offer=offer)


# ------------------ Видалення пропозиції ------------------
@main.route('/contractor/delete_offer/<int:offer_id>', methods=['POST'])
@login_required
def delete_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    if offer.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    db.session.delete(offer)
    db.session.commit()
    return redirect(url_for('main.dashboard', role='contractor'))


# ------------------ Перегляд пропозицій ------------------
@main.route('/offers')
@login_required
def view_offers():
    if session.get('role') != 'customer':
        return "Доступ лише для замовників", 403

    offers = Offer.query.all()
    return render_template('offers_list.html', offers=offers)


# ------------------ Детальна сторінка пропозиції ------------------
@main.route('/offer/<int:offer_id>')
@login_required
def offer_detail(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    return render_template('offer_detail.html', offer=offer)


# ------------------ Створення замовлення ------------------
@main.route('/order/create/<int:offer_id>', methods=['GET', 'POST'])
@login_required
def create_order(offer_id):
    if session.get('role') != 'customer':
        return "Доступ лише для замовників", 403

    offer = Offer.query.get_or_404(offer_id)

    if request.method == 'POST':
        stl_filename = "model.stl"
        estimated_weight = 50.0
        estimated_price = estimated_weight * offer.price_per_gram

        order = Order(
            stl_filename=stl_filename,
            estimated_weight=estimated_weight,
            estimated_price=estimated_price,
            offer_id=offer.id,
            customer_id=current_user.id,
            contractor_id=offer.contractor.id
        )
        db.session.add(order)
        db.session.commit()

        return redirect(url_for('main.dashboard', role='customer'))

    return render_template('create_order.html', offer=offer)


# ------------------ Редагування профілю ------------------
@main.route('/profile/<role>', methods=['GET', 'POST'])
@login_required
def edit_profile(role):
    if session.get('role') != role:
        return "Доступ заборонено", 403

    user = Customer.query.get(current_user.id) if role == 'customer' else Contractor.query.get(current_user.id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        file = request.files.get('profile_image')

        if role == 'customer':
            user.full_name = new_name
        else:
            user.company_name = new_name

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            save_path = os.path.join('app', 'static', 'uploads', filename)
            file.save(save_path)
            user.profile_image = filename

        db.session.commit()
        return redirect(url_for('main.dashboard', role=role))

    return render_template('edit_profile.html', user=user, role=role)
