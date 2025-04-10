from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

from app import db

class Customer(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_image = db.Column(db.String(200), default='default-avatar.png')  # Фото профілю
    rating = db.Column(db.Float, default=0.0)

    orders = db.relationship('Order', backref='customer', lazy=True)

class Contractor(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_image = db.Column(db.String(200), default='default-avatar.png')  # Фото профілю
    rating = db.Column(db.Float, default=0.0)

    offers = db.relationship('Offer', backref='contractor', lazy=True)
    orders = db.relationship('Order', backref='contractor', lazy=True)

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material = db.Column(db.String(100), nullable=False)
    layer_height = db.Column(db.Float, nullable=False)
    price_per_gram = db.Column(db.Float, nullable=False)
    max_size = db.Column(db.String(100))
    min_size = db.Column(db.String(100))

    contractor_id = db.Column(db.Integer, db.ForeignKey('contractor.id'), nullable=False)
    orders = db.relationship('Order', backref='offer', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stl_filename = db.Column(db.String(255), nullable=False)
    estimated_weight = db.Column(db.Float)
    estimated_price = db.Column(db.Float)
    status = db.Column(db.String(50), default='Очікує підтвердження')

    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    contractor_id = db.Column(db.Integer, db.ForeignKey('contractor.id'))

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
