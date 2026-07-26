from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

import logging

import paypalrestsdk

from dotenv import load_dotenv
import os

paypalrestsdk.configure({

    "mode": "sandbox",

    "client_id": os.environ.get("PAYPAL_CLIENT_ID"),

    "client_secret": os.environ.get("PAYPAL_SECRET")

})

app = Flask(__name__)

logging.basicConfig(
    filename="foxlab.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

app.secret_key = os.environ.get("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///foxlab.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

class Purchase(db.Model):

    id = db.Column(
            db.Integer,
                primary_key=True
    )
        
    username = db.Column(
                db.String(80),
                nullable=False
    )
        
    product = db.Column(
                db.String(100),
                nullable=False
    )
        
    paid = db.Column(
                db.Boolean,
                default=False
    )

class Product(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.String(255)
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    image = db.Column(
        db.String(100),
        nullable=False
    )

class Order(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(80),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default="pending"
    )


@app.route("/")
def home ():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session["username"] = user.username

            logging.info(
        f"Successful login: {user.username}"
    )

            logging.warning(
    f"Failed login attempt: {username}"
)

            return redirect(url_for("dashboard"))

        return "Invalid username or password."

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/premium")
def premium():

    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    order = Order.query.filter_by(
    username=username,
    status="paid"
).first()

    return render_template(
        "premium.html",
        purchased=order is not None
    )

@app.route("/buy/<int:id>")
def buy(id):

    if "username" not in session:
        return redirect(url_for("login"))

    product = Product.query.get_or_404(id)

    order = Order(
        username=session["username"],
        product_id=product.id,
        status="pending"
    )

    db.session.add(order)
    db.session.commit()

    logging.info(
    f"Order created: user={session['username']} product={product.name}"
)

    return render_template(
        "payment.html",
        order=order,
        product=product
    )
    

@app.route("/product/<int:id>")
def product(id):

    product = Product.query.get_or_404(id)

    return render_template(
        "product.html",
        product=product
    )

@app.route("/payment-success/<int:id>")
def payment_success(id):

    if "username" not in session:
        return redirect(url_for("login"))

    order = Order.query.get_or_404(id)

    order.status = "paid"

    db.session.commit()

    return render_template(
        "payment_success.html",
        order=order
    )

@app.route("/create-payment/<int:id>")
def create_payment(id):

    if "username" not in session:
        return redirect(url_for("login"))


    order = Order.query.get_or_404(id)


    payment = paypalrestsdk.Payment({

        "intent": "sale",

        "payer": {

            "payment_method": "paypal"

        },

        "redirect_urls": {

            "return_url":
            "http://127.0.0.1:5000/payment-success/" + str(order.id),

            "cancel_url":
            "http://127.0.0.1:5000/payment-cancel"

        },

        "transactions": [

            {

                "amount": {

                    "total": "5.00",

                    "currency": "GBP"

                },

                "description":
                "Fox Premium Image"

            }

        ]

    })


    if payment.create():

        for link in payment.links:

            if link.rel == "approval_url":

                return redirect(link.href)


    return "Payment creation failed"

@app.route("/payment-cancel")
def payment_cancel():

    return "Payment cancelled"


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run()