from __future__ import annotations
from datetime import datetime
from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(90), nullable=False)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="Administrador")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    color = db.Column(db.String(20), default="green")
    icon = db.Column(db.String(30), default="wallet")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    unit = db.Column(db.String(30), default="un")
    unit_price = db.Column(db.Float, nullable=False, default=0)
    default_quantity = db.Column(db.Float, nullable=False, default=1)
    active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(180), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(12), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    entity = db.Column(db.String(120), default="")
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(80), default="PIX")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    category = db.relationship("Category")
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class FixedRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(12), nullable=False, default="saida")
    title = db.Column(db.String(120), nullable=False)
    entity = db.Column(db.String(120), default="")
    amount = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(80), default="PIX")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    category = db.relationship("Category")
    day_of_month = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)
    last_generated_month = db.Column(db.String(7), default="")
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship(
        "FixedRecordItem", backref="fixed_record",
        cascade="all, delete-orphan", lazy=True
    )


class FixedRecordItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fixed_record_id = db.Column(
        db.Integer, db.ForeignKey("fixed_record.id"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit = db.Column(db.String(30), default="un")
    unit_price = db.Column(db.Float, nullable=False, default=0)
    amount = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.String(160), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.String(255), default="")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
