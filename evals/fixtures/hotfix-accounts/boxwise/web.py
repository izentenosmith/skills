"""The HTTP layer the storefront mounts: form posts in, (status, message) out."""
from . import accounts, auth
from .mailer import send_reset_link

NOT_FOUND = "We couldn't find an account with that email."


def post_signup(db, form):
    try:
        uid = accounts.signup(db, form.get("email", ""), form.get("password", ""))
    except accounts.InvalidEmail:
        return 400, "That doesn't look like an email address."
    except accounts.EmailTaken:
        return 409, "There's already an account with that email. Sign in instead?"
    except ValueError:
        return 400, f"Passwords need at least {accounts.MIN_PASSWORD} characters."
    return 201, f"Welcome! Your account number is {uid}."


def post_login(db, form):
    uid = auth.login(db, form.get("email", ""), form.get("password", ""))
    if uid is None:
        return 401, "That email and password don't match."
    return 200, f"Signed in as {accounts.get_user(db, uid)['email']}."


def post_reset_request(db, form):
    email = form.get("email", "")
    token = auth.request_password_reset(db, email)
    if token is None:
        return 404, NOT_FOUND
    send_reset_link(accounts.find_by_email(db, email)["email"], token)
    return 200, "Check your inbox for a reset link."
