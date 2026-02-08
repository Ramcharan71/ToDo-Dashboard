from functools import wraps
import os

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Todo


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    def login_required(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapper

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash("All fields are required.", "danger")
                return render_template("register.html")

            if User.query.filter_by(email=email).first():
                flash("Email is already registered.", "danger")
                return render_template("register.html")

            password_hash = generate_password_hash(password)
            user = User(name=name, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html")

            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Welcome back, {}.".format(user.name), "success")
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if not user:
                flash("No account found for that email.", "danger")
                return render_template("forgot_password.html")

            session["reset_email"] = user.email
            flash("Email verified. Set a new password.", "success")
            return redirect(url_for("reset_password"))

        return render_template("forgot_password.html")

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        reset_email = session.get("reset_email")
        if not reset_email:
            flash("Please verify your email first.", "warning")
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not password or password != confirm_password:
                flash("Passwords do not match.", "danger")
                return render_template("reset_password.html")

            user = User.query.filter_by(email=reset_email).first()
            if not user:
                flash("Account not found.", "danger")
                return redirect(url_for("forgot_password"))

            user.password_hash = generate_password_hash(password)
            db.session.commit()
            session.pop("reset_email", None)
            flash("Password reset successful. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("reset_password.html")

    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        user_id = session.get("user_id")

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("Todo title cannot be empty.", "danger")
            else:
                todo = Todo(title=title, user_id=user_id)
                db.session.add(todo)
                db.session.commit()
                flash("Todo added.", "success")
            return redirect(url_for("dashboard"))

        todos = Todo.query.filter_by(user_id=user_id).order_by(Todo.created_at.desc()).all()
        return render_template("dashboard.html", todos=todos)

    @app.route("/todos/<int:todo_id>/delete", methods=["POST"])
    @login_required
    def delete_todo(todo_id):
        user_id = session.get("user_id")
        todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
        if not todo:
            flash("Todo not found.", "danger")
            return redirect(url_for("dashboard"))

        db.session.delete(todo)
        db.session.commit()
        flash("Todo deleted.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/todos/<int:todo_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_todo(todo_id):
        user_id = session.get("user_id")
        todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
        if not todo:
            flash("Todo not found.", "danger")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("Todo title cannot be empty.", "danger")
                return render_template("edit_todo.html", todo=todo)

            todo.title = title
            db.session.commit()
            flash("Todo updated.", "success")
            return redirect(url_for("dashboard"))

        return render_template("edit_todo.html", todo=todo)

    @app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
    @login_required
    def toggle_todo(todo_id):
        user_id = session.get("user_id")
        todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
        if not todo:
            flash("Todo not found.", "danger")
            return redirect(url_for("dashboard"))

        todo.is_complete = not todo.is_complete
        db.session.commit()
        flash("Todo updated.", "success")
        return redirect(url_for("dashboard"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
