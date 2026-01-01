from extensions import db
from flask_login import UserMixin

class AuthUser(db.Model, UserMixin):
    """Application login user - synced from Genesys Cloud OAuth"""
    __tablename__ = 'auth_user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    genesys_user_id = db.Column(db.String(36), nullable=True)  # Genesys Cloud User ID
    name = db.Column(db.String(200), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)  # Dummy for OAuth users
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login = db.Column(db.DateTime, nullable=True)
    
    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<AuthUser {self.email}>'
