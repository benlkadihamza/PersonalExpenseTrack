from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    description = db.Column(db.Text, nullable=True)
    revenu = db.Column(db.Float, nullable=False, default=0.0)
    depense = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def net(self):
        return (self.revenu or 0.0) - (self.depense or 0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'description': self.description or '',
            'revenu': self.revenu,
            'depense': self.depense,
            'net': self.net,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=True)

    @classmethod
    def get_val(cls, key, default=None):
        setting = db.session.get(cls, key)
        return setting.value if setting and setting.value is not None else default

    @classmethod
    def set_val(cls, key, value):
        setting = db.session.get(cls, key)
        if not setting:
            setting = cls(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)
        db.session.commit()
