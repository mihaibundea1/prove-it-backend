# utils/user.py

from flask import g
from clerk_sdk_python import Clerk

clerk = Clerk()

def get_current_user():
    """Get the current user's details from Clerk"""
    if hasattr(g, 'user_id'):
        return clerk.users.get(g.user_id)
    return None

def get_user_metadata():
    """Get the current user's public metadata"""
    user = get_current_user()
    if user:
        return user.public_metadata
    return None