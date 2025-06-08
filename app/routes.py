from flask import Blueprint, render_template, request, redirect, url_for, session
from flask import jsonify
from sqlalchemy import func
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import db, Customer, Contractor, Offer, Order, ChatMessage, Rating
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from sqlalchemy import and_
import os

# --- перелік стандартних матеріалів 3D-друку (можеш редагувати) ---
MATERIALS = ["PLA", "ABS", "PETG", "TPU", "Nylon", "Resin", "ASA", "PC"]

ACTIVE_STATUSES = (
    'Draft',
    'Очікує підтвердження',
    'У виконанні',
    'Друк завершено'
)

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
    role = request.args.get('role') or session.get('role')
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
                .filter_by(contractor_id=current_user.id, status='Очікує підтвердження')
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
        # якщо обрано «other» — забираємо текст із поля material_other
        material = request.form.get('material')
        if material == 'other':
            material = request.form.get('material_other', '').strip() or 'Other'

        layer_height   = float(request.form['layer_height'])
        price_per_gram = float(request.form['price_per_gram'])
        max_size       = request.form['max_size']
        min_size       = request.form['min_size']

        offer = Offer(
            material       = material,
            layer_height   = layer_height,
            price_per_gram = price_per_gram,
            max_size       = max_size,
            min_size       = min_size,
            contractor_id  = current_user.id
        )
        db.session.add(offer)
        db.session.commit()

        # зберігаємо до 10 фотографій-прикладів (можеш змінити ліміт)
        files         = request.files.getlist('images')
        examples_path = os.path.join('app', 'static', 'examples')
        os.makedirs(examples_path, exist_ok=True)

        for idx, f in enumerate(files[:10], start=1):
            if f and f.filename:
                fname = f'offer_{offer.id}_example_{idx}.jpg'
                f.save(os.path.join(examples_path, fname))

        return redirect(url_for('main.dashboard', role='contractor'))

    # GET — показуємо форму зі списком MATERIALS
    return render_template('create_offer.html', materials=MATERIALS)

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
        material = request.form.get('material')
        if material == 'other':
            material = request.form.get('material_other', '').strip() or 'Other'

        offer.material       = material
        offer.layer_height   = float(request.form['layer_height'])
        offer.price_per_gram = float(request.form['price_per_gram'])
        offer.max_size       = request.form['max_size']
        offer.min_size       = request.form['min_size']

        # якщо завантажені нові фото — перезаписуємо (теж до 10 шт.)
        files = request.files.getlist('images')
        if files and any(f.filename for f in files):
            examples_path = os.path.join('app', 'static', 'examples')
            os.makedirs(examples_path, exist_ok=True)
            for idx, f in enumerate(files[:10], start=1):
                if f and f.filename:
                    fname = f'offer_{offer.id}_example_{idx}.jpg'
                    f.save(os.path.join(examples_path, fname))

        db.session.commit()
        return redirect(url_for('main.dashboard', role='contractor'))

    # GET — показуємо форму, передаючи список MATERIALS і сам offer
    return render_template('edit_offer.html', offer=offer, materials=MATERIALS)

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

    from sqlalchemy.orm import joinedload
    q = Offer.query.options(joinedload(Offer.contractor))

    # ---- фільтрація ----
    material = request.args.get('material')
    if material:
        q = q.filter_by(material=material)

    max_price = request.args.get('max_price', type=float)
    if max_price is not None:
        q = q.filter(Offer.price_per_gram <= max_price)

    # === Новий фільтр: рейтинг ===
    min_rating = request.args.get('min_rating', type=float)
    if min_rating is not None:
        q = q.join(Offer.contractor).filter(Contractor.rating >= min_rating)

    sort = request.args.get('sort')
    if sort == 'price_asc':
        q = q.order_by(Offer.price_per_gram.asc())
    elif sort == 'price_desc':
        q = q.order_by(Offer.price_per_gram.desc())
    elif sort == 'rating_desc':
        q = q.join(Offer.contractor).order_by(Contractor.rating.desc())
    elif sort == 'rating_asc':
        q = q.join(Offer.contractor).order_by(Contractor.rating.asc())
    elif sort == 'value':
        max_price = db.session.query(func.max(Offer.price_per_gram)).scalar() or 1
        q = q.join(Offer.contractor)\
            .add_columns((0.5*Contractor.rating + 0.5*(max_price/Offer.price_per_gram)).label('value_score'))\
            .order_by(db.desc('value_score'))

       # Якщо повернувся кортеж/Row — дістаємо перший елемент (Offer)
    offers = []
    for o in q.all():
        # Якщо це кортеж (tuple)
        if isinstance(o, tuple):
            offers.append(o[0])
        # Якщо це Row (новий SQLAlchemy)
        elif hasattr(o, '_mapping') and hasattr(o, '_fields'):
            offers.append(getattr(o, o._fields[0]))
        else:
            offers.append(o)

    # список унікальних матеріалів для фільтра
    materials = db.session.query(Offer.material).distinct().order_by(Offer.material).all()
    materials = [m[0] for m in materials]

    return render_template('offers_list.html',
                           offers=offers,
                           materials=materials,
                           static_files=set(os.listdir('app/static/examples')))

# ------------------ Детальна сторінка пропозиції ------------------
@main.route('/offer/<int:offer_id>')
@login_required
def offer_detail(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    role  = session.get('role')

    order_id    = request.args.get('order', type=int)
    order       = None
    chat_orders = []

    # --- ДЛЯ ЗАМОВНИКА ---
    if role == 'customer':
        # Беремо будь-яке останнє замовлення (Draft теж підходить)
        order = (Order.query
                 .filter_by(offer_id=offer_id, customer_id=current_user.id)
                 .order_by(Order.timestamp.desc())
                 .first())
        # Якщо зовсім нема — створюємо "Draft" (без STL)
        if order is None:
            order = Order(
                stl_filename      = '__draft__.stl',
                estimated_weight  = 0,
                estimated_price   = 0,
                status            = 'Draft',
                offer_id          = offer_id,
                customer_id       = current_user.id,
                contractor_id     = offer.contractor.id
            )
            db.session.add(order)
            db.session.commit()
            db.session.refresh(order)
        show_chat = True
        can_chat = True

   # ДЛЯ ДРУКАРЯ
    elif role == 'contractor':
        all_orders = (
            Order.query
            .filter_by(offer_id=offer_id, contractor_id=current_user.id)
            .order_by(Order.timestamp.desc())
            .all()
        )
        seen = set()
        chat_orders = []
        for o in all_orders:
            # додаємо, якщо або не draft, або є хоч одне повідомлення
            if o.customer_id not in seen and (o.stl_filename != '__draft__.stl' or len(o.messages) > 0):
                chat_orders.append(o)
                seen.add(o.customer_id)
        if order_id:
            order = Order.query.get_or_404(order_id)
        elif chat_orders:
            order = chat_orders[0]
        else:
            order = None
        show_chat = order is not None
        can_chat = show_chat

    chat_cnt = len(chat_orders) if role == 'contractor' else 1

    rated = False
    if order and role == 'customer':
        from app.models import Rating
        rated = Rating.query.filter_by(order_id=order.id, customer_id=current_user.id).first() is not None


    return render_template(
        'offer_detail.html',
        offer     = offer,
        role      = role,
        order     = order,
        chats     = chat_orders if role == 'contractor' else [],
        chat_cnt  = chat_cnt,
        show_chat = show_chat,
        can_chat  = can_chat,
        rated     = rated  # <-- ОБОВ’ЯЗКОВО!
    )


# ------------------ Створення / повторне створення замовлення ------------------
@main.route('/order/create/<int:offer_id>', methods=['GET', 'POST'])
@login_required
def create_order(offer_id):
    if session.get('role') != 'customer':
        return "Доступ лише для замовників", 403

    offer = Offer.query.get_or_404(offer_id)

    # ───────────── POST ─────────────
    if request.method == 'POST':
        file = request.files.get('stl_file')
        if not file or not file.filename.endswith('.stl'):
            return "Потрібен STL-файл!", 400

        # шукаємо «активне» замовлення (Draft / Очікує … / …)
        active = (Order.query
                  .filter_by(offer_id      = offer_id,
                             customer_id   = current_user.id,
                             contractor_id = offer.contractor.id)
                  .filter(Order.status.in_(ACTIVE_STATUSES),
                          Order.stl_filename != '__draft__.stl')
                  .first())

        # якщо є активне – просто перейдемо до нього (не даємо плодити дублікати)
        if active:
            return redirect(url_for('main.offer_detail',
                                    offer_id = offer_id,
                                    order    = active.id))

        # якщо ж останнє замовлення було **відхилено**, — ПЕРЕВИКОРИСТОВУЄМО його
        rejected = (Order.query
                    .filter_by(offer_id      = offer_id,
                               customer_id   = current_user.id,
                               contractor_id = offer.contractor.id,
                               status        = 'Відхилено')
                    .order_by(Order.timestamp.desc())
                    .first())

        # ── зберігаємо файл ──
        stl_dir  = os.path.join('app', 'static', 'stl_files')
        os.makedirs(stl_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file.save(os.path.join(stl_dir, filename))

        # TODO: обчислюємо вагу реально
        estimated_weight = 50.0
        estimated_price  = estimated_weight * offer.price_per_gram

        if rejected:               # ▲ оновлюємо «відхилене» замовлення
            rejected.stl_filename     = filename
            rejected.estimated_weight = estimated_weight
            rejected.estimated_price  = estimated_price
            rejected.delivery_info    = request.form.get('delivery_info')
            rejected.status           = 'Очікує підтвердження'
            db.session.commit()
            oid = rejected.id
        else:                       # ▼ створюємо геть новий Order
            new_order = Order(
                stl_filename      = filename,
                estimated_weight  = estimated_weight,
                estimated_price   = estimated_price,
                delivery_info     = request.form.get('delivery_info'),
                offer_id          = offer.id,
                customer_id       = current_user.id,
                contractor_id     = offer.contractor.id,
                status            = 'Очікує підтвердження'
            )
            db.session.add(new_order)
            db.session.commit()
            oid = new_order.id

        return redirect(url_for('main.offer_detail',
                                offer_id = offer.id,
                                order    = oid))
    # ───────────── GET ─────────────
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
    if not file or not file.filename:
        return "Потрібно додати фото звіту!", 400

    examples_path = os.path.join('app', 'static', 'examples')
    os.makedirs(examples_path, exist_ok=True)

    fname = f'order_{order.id}_progress.jpg'
    file.save(os.path.join(examples_path, fname))
    order.progress_image = fname

    img_msg = ChatMessage(
        order_id    = order.id,
        sender_id   = current_user.id,
        sender_role = 'contractor',
        text        = '[img]' + fname
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

# ------------------ Оцінити друкара ------------------
@main.route('/order/<int:order_id>/rate', methods=['POST'])
@login_required
def rate_order(order_id):
    order = Order.query.get_or_404(order_id)
    # --- доступ лише для клієнта цього замовлення ---
    if session.get('role') != 'customer' or order.customer_id != current_user.id:
        return "Доступ заборонено", 403

    if order.status != 'Відправлено':
        return "Оцінити можна тільки після відправки", 400

    if Rating.query.filter_by(order_id=order.id, customer_id=current_user.id).first():
        return "Оцінку вже виставлено", 400

    try:
        score = int(request.form.get('score', 0))
    except ValueError:
        score = 0
    score = max(1, min(score, 5))

    r = Rating(order_id=order.id,
               customer_id=current_user.id,
               contractor_id=order.contractor_id,
               score=score)
    db.session.add(r)

    # Перерахунок середнього рейтингу для цього друкаря
    avg = db.session.query(db.func.avg(Rating.score)) \
                    .filter(Rating.contractor_id == order.contractor_id) \
                    .scalar() or 0
    contractor = Contractor.query.get(order.contractor_id)
    contractor.rating = round(avg, 2)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 204
    return redirect(url_for('main.offer_detail', offer_id=order.offer_id, order=order.id))


# ------------------ CHAT ------------------
def _allowed(order):
    return ((session['role']=='customer'   and order.customer_id==current_user.id) or
            (session['role']=='contractor' and order.contractor_id==current_user.id))


# GET історія
@main.route('/order/<int:oid>/chat', methods=['GET'])
@login_required
def chat_messages(oid):
    order = Order.query.get_or_404(oid)
    if not _allowed(order):
        return '', 403

    # 1) Чат дозволений тільки якщо замовник вже створив хоч одне замовлення під цю пропозицію
    # (інакше – повертаємо порожній список)
    if session['role'] == 'contractor':
        # Чи є хоча б одне замовлення цього клієнта під цю пропозицію?
        first_order = (Order.query
            .filter_by(
                offer_id=order.offer_id,
                customer_id=order.customer_id,
                contractor_id=order.contractor_id
            )
            .order_by(Order.timestamp)
            .first()
        )
        # Якщо нема – чат порожній
        if not first_order:
            return jsonify([])

    # 2) Дістаємо всі order.id для цієї пари (пропозиція + дві особи)
    thread_orders = (Order.query
        .with_entities(Order.id)
        .filter_by(
            offer_id=order.offer_id,
            customer_id=order.customer_id,
            contractor_id=order.contractor_id
        )
    ).subquery()

    # 3) Витягуємо всі повідомлення в цій "гілці"
    msgs = (ChatMessage.query
        .filter(ChatMessage.order_id.in_(thread_orders.select()))
        .order_by(ChatMessage.created_at)
        .all()
    )


    return jsonify([{
        "mine":  (m.sender_id == current_user.id and m.sender_role == session['role']),
        "role":  m.sender_role,
        "text":  m.text,
        "img":   (m.text.startswith('[img]') and url_for('static', filename='examples/' + m.text[5:])) or None,
        "time":  m.created_at.strftime('%H:%M')
    } for m in msgs])

# POST нове повідомлення
@main.route('/order/<int:oid>/chat', methods=['POST'])
@login_required
def chat_send(oid):
    order = Order.query.get_or_404(oid)
    if not _allowed(order):
        return '', 403
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


