from flask import Blueprint, render_template, request, redirect, url_for, session
from flask import jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import db, Customer, Contractor, Offer, Order, ChatMessage
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import os

from app.models import db, Customer, Contractor, Offer, Order

main = Blueprint('main', __name__)

# ------------------ Головна ------------------
@main.route('/')
def home():
    stats = {
        "customers": Customer.query.count(),
        "contractors": Contractor.query.count(),
        "offers": Offer.query.count()
    }
    return render_template('index.html', stats=stats)

# ------------------ Реєстрація (обʼєднана) ------------------
@main.route('/register', methods=['GET', 'POST'])
def register():
    role = request.args.get('role')  # ?role=customer | ?role=contractor
    if not role or role not in ['customer', 'contractor']:
        return "Потрібен ?role=customer чи ?role=contractor", 400

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        file = request.files.get('profile_image')

        if password != confirm:
            return "Паролі не співпадають!"

        model = Customer if role == 'customer' else Contractor
        if model.query.filter_by(email=email).first():
            return "Email вже використовується!"

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        filename = 'default-avatar.png'

        # Якщо додали фото
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            save_path = os.path.join('app', 'static', 'uploads', filename)
            file.save(save_path)

        if role == 'customer':
            new_user = Customer(full_name=name, email=email, password=hashed_password, profile_image=filename)
        else:
            new_user = Contractor(company_name=name, email=email, password=hashed_password, profile_image=filename)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('main.login') + f'?role={role}')

    return render_template('register.html', role=role)

# ------------------ Вхід (обʼєднаний) ------------------
@main.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role')  # ?role=customer | ?role=contractor
    if not role or role not in ['customer', 'contractor']:
        return "Потрібен ?role=customer чи ?role=contractor", 400

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

        # показуємо лише ті замовлення, де вже є хоч одне повідомлення
        chats = (Order.query
                 .filter_by(contractor_id=current_user.id)
                 .filter(Order.messages.any())        # ← головне фільтрування
                 .order_by(Order.timestamp.desc())
                 .all())

        from datetime import datetime
        return render_template(
            'dashboard.html',
            user=current_user,
            role=role,
            offers=offers,
            chats=chats,
            now=datetime.utcnow()
        )

    elif role == 'customer':
        return redirect(url_for('main.view_offers'))

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

        # Збереження фото прикладів (до 3)
        files = request.files.getlist('images')
        examples_path = os.path.join('app', 'static', 'examples')
        os.makedirs(examples_path, exist_ok=True)

        for idx, f in enumerate(files[:3]):
            if f and f.filename:
                fname = f'offer_{offer.id}_example_{idx+1}.jpg'
                f.save(os.path.join(examples_path, fname))

        return redirect(url_for('main.dashboard', role='contractor'))

    return render_template('create_offer.html')

# ------------------ Редагування пропозиції ------------------
@main.route('/contractor/edit_offer/<int:offer_id>', methods=['GET', 'POST'])
@login_required
def edit_offer(offer_id):
    if session.get('role') != 'contractor':
        return "Доступ заборонено", 403

    offer = Offer.query.get_or_404(offer_id)
    if offer.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    if request.method == 'POST':
        offer.material = request.form['material']
        offer.layer_height = float(request.form['layer_height'])
        offer.price_per_gram = float(request.form['price_per_gram'])
        offer.max_size = request.form['max_size']
        offer.min_size = request.form['min_size']

        # якщо додано нові фото — зберегти (замість старих)
        files = request.files.getlist('images')
        if files and any(f.filename for f in files):
            examples_path = os.path.join('app', 'static', 'examples')
            os.makedirs(examples_path, exist_ok=True)

            # зберігаємо до 3 штук
            for idx, f in enumerate(files[:3]):
                if f and f.filename:
                    fname = f'offer_{offer.id}_example_{idx+1}.jpg'
                    f.save(os.path.join(examples_path, fname))

        db.session.commit()
        return redirect(url_for('main.dashboard', role='contractor'))

    return render_template('edit_offer.html', offer=offer)

# ------------------ Видалення пропозиції ------------------
@main.route('/contractor/delete_offer/<int:offer_id>', methods=['POST'])
@login_required
def delete_offer(offer_id):
    if session.get('role') != 'contractor':
        return "Доступ заборонено", 403

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
    files  = set(os.listdir('app/static/examples'))
    return render_template('offers_list.html',
                           offers=offers,
                           static_files=files)


# ------------------ Детальна сторінка пропозиції ------------------
@main.route('/offer/<int:offer_id>')
@login_required
def offer_detail(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    role  = session.get('role')

    # якщо в URL передали конкретний order (друкар відкрив чат-посилання)
    order_id = request.args.get('order', type=int)
    order    = None

    # ───── клієнт ────────────────────────────────────────────────
    if role == 'customer':
        order = (Order.query
                 .filter_by(offer_id=offer_id, customer_id=current_user.id)
                 .first())

        if order is None:                     # створюємо «Draft» лише клієнту
            order = Order(
                stl_filename='__draft__.stl',
                estimated_weight=0,
                estimated_price=0,
                status='Draft',
                offer_id=offer_id,
                customer_id=current_user.id,
                contractor_id=offer.contractor.id
            )
            db.session.add(order)
            db.session.commit()

    # ───── друкар ───────────────────────────────────────────────
    else:  # contractor
        if order_id:                          # 👉 прийшли з “Відкрити чат”
            order = Order.query.get_or_404(order_id)

            # захист: чужий order або не цієї пропозиції
            if order.contractor_id != current_user.id or order.offer_id != offer_id:
                return "Доступ заборонено", 403

        # якщо конкретний order не задано або не пройшов перевірку
        if order is None:
            # 1) шукаємо замовлення з уже існуючим чатом
            order = (Order.query
                     .filter_by(offer_id=offer_id)
                     .filter(Order.messages.any())
                     .order_by(Order.timestamp.desc())
                     .first())

        # 2) якщо чатів зовсім нема — беремо найновіший order (може бути Draft)
        if order is None:
            order = (Order.query
                     .filter_by(offer_id=offer_id)
                     .order_by(Order.timestamp.desc())
                     .first())

    return render_template('offer_detail.html',
                           offer=offer,
                           role=role,
                           order=order)

# ------------------ Створення замовлення ------------------
@main.route('/order/create/<int:offer_id>', methods=['GET', 'POST'])
@login_required
def create_order(offer_id):
    if session.get('role') != 'customer':
        return "Доступ лише для замовників", 403

    offer = Offer.query.get_or_404(offer_id)

    if request.method == 'POST':
        file = request.files.get('stl_file')
        if not file or not file.filename.endswith('.stl'):
            return "Потрібен STL-файл!", 400

        # Створюємо директорію для STL-файлів, якщо її немає
        stl_path = os.path.join('app', 'static', 'stl_files')
        os.makedirs(stl_path, exist_ok=True)

        filename = secure_filename(file.filename)
        file.save(os.path.join(stl_path, filename))

        estimated_weight = 50.0  # заглушка
        estimated_price = estimated_weight * offer.price_per_gram

        print('Адреса доставки:', request.form.get('delivery_info'))


        order = Order(
            stl_filename=filename,
            estimated_weight=estimated_weight,
            estimated_price=estimated_price,
            delivery_info=request.form.get('delivery_info'),
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

    if role == 'customer':
        user = Customer.query.get(current_user.id)
    else:
        user = Contractor.query.get(current_user.id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        file = request.files.get('profile_image')

        if role == 'customer':
            user.full_name = new_name
        else:
            user.company_name = new_name

        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join('app', 'static', 'uploads', filename)
            file.save(save_path)
            user.profile_image = filename

        db.session.commit()
        return redirect(url_for('main.dashboard', role=role))

    return render_template('edit_profile.html', user=user, role=role)

# ------------------ Перегляд чужого профілю ------------------
@main.route('/profile/view/<int:user_id>')
@login_required
def view_profile(user_id):
    # шукаємо друкаря
    user = Contractor.query.get(user_id)
    if user:
        return render_template('view_profile.html', user=user, role='contractor')
    # якщо не знайшли, шукаємо customer
    user = Customer.query.get_or_404(user_id)
    return render_template('view_profile.html', user=user, role='customer')

# ------------------ Прийняти замовлення ------------------
@main.route('/order/<int:order_id>/accept', methods=['POST'])
@login_required
def accept_order(order_id):
    order = Order.query.get_or_404(order_id)
    if session.get('role') != 'contractor' or order.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    order.status = "У виконанні"
    db.session.commit()
    return redirect(url_for('main.offer_detail', offer_id=order.offer_id))

# ------------------ Відхилити замовлення ------------------
@main.route('/order/<int:order_id>/reject', methods=['POST'])
@login_required
def reject_order(order_id):
    order = Order.query.get_or_404(order_id)
    if session.get('role') != 'contractor' or order.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    reason = request.form.get('rejection_reason')
    if not reason:
        return "Потрібно вказати причину!", 400

    order.status = "Відхилено"
    order.cancellation_reason = reason
    db.session.commit()
    return redirect(url_for('main.offer_detail', offer_id=order.offer_id))
# ------------------ Завершити друк ------------------
@main.route('/order/<int:order_id>/finish', methods=['POST'])
@login_required
def finish_print(order_id):
    order = Order.query.get_or_404(order_id)
    if session.get('role') != 'contractor' or order.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    file = request.files.get('progress_img')
    if file and file.filename:
        fname = f'order_{order.id}_progress.jpg'
        path  = os.path.join('app', 'static', 'examples', fname)
        file.save(path)
        order.progress_image = fname

        # 🆕 додаємо повідомлення‑картинку в чат
        img_msg = ChatMessage(
            order_id    = order.id,
            sender_id   = current_user.id,
            sender_role = 'contractor',
            text        = '[img]' + fname        # спец‑тег
        )
        db.session.add(img_msg)

    order.status = "Друк завершено"
    db.session.commit()
    return redirect(url_for('main.offer_detail', offer_id=order.offer_id))

# ------------------ Відправити поштою ------------------
@main.route('/order/<int:order_id>/ship', methods=['POST'])
@login_required
def ship_order(order_id):
    order = Order.query.get_or_404(order_id)
    if session.get('role') != 'contractor' or order.contractor_id != current_user.id:
        return "Доступ заборонено", 403

    order.status = "Відправлено"
    db.session.commit()
    return redirect(url_for('main.offer_detail', offer_id=order.offer_id)) 

# ------------------ CHAT ------------------
def _allowed(order):
    return ((session['role']=='customer'   and order.customer_id==current_user.id) or
            (session['role']=='contractor' and order.contractor_id==current_user.id))

# GET усі повідомлення
@main.route('/order/<int:oid>/chat', methods=['GET'])
@login_required
def chat_messages(oid):
    order = Order.query.get_or_404(oid)
    if not _allowed(order):
        return '', 403

    msgs = (ChatMessage.query
            .filter_by(order_id=oid)
            .order_by(ChatMessage.created_at)
            .all())

    return jsonify([{
        "mine":  (m.sender_id == current_user.id and m.sender_role == session['role']),
        "role":  m.sender_role,
        "text":  m.text,
        "img":   (m.text.startswith('[img]') and
                  url_for('static', filename='examples/' + m.text[5:])) or None,
        "time":  m.created_at.strftime('%H:%M')
    } for m in msgs])

# POST нове повідомлення
@main.route('/order/<int:oid>/chat', methods=['POST'])
@login_required
def chat_send(oid):
    order = Order.query.get_or_404(oid)
    if not _allowed(order):
        return '', 403

    # перше повідомлення може надіслати тільки customer
    first = ChatMessage.query.filter_by(order_id=oid).first() is None
    if first and session['role'] != 'customer':
        return jsonify({"error": "Лише замовник може почати чат"}), 403

    txt = request.form.get('text','').strip()
    if not txt:
        return '', 400

    m = ChatMessage(order_id=oid,
                    sender_id=current_user.id,
                    sender_role=session['role'],
                    text=txt)
    db.session.add(m)
    db.session.commit()

    return jsonify({
        "mine": True,
        "role": m.sender_role,
        "text": m.text,
        "time": m.created_at.strftime('%H:%M')
    }), 201

