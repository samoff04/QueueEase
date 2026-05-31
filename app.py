from flask import Flask,render_template,request,redirect,session,flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

app=Flask(__name__)
app.secret_key="queueease_secret"

app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///queueease.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

db=SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(100),unique=True,nullable=False)
    password=db.Column(db.String(200),nullable=False)
    appointments=db.relationship("Appointment",backref="user",cascade="all,delete",lazy=True)

class Appointment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    service=db.Column(db.String(100),nullable=False)
    appointment_date=db.Column(db.String(50),nullable=False)
    token_number=db.Column(db.Integer,nullable=False)
    status=db.Column(db.String(50),default="Booked")
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_status(count):
    if count<=3:
        return "Low"
    elif count<=7:
        return "Moderate"
    return "Busy"

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/login",methods=["GET","POST"])
def login():
    if "user_id" in session:
        return redirect("/dashboard")

    if request.method=="POST":
        username=request.form["username"]
        password=hash_password(request.form["password"])

        user=User.query.filter_by(
            username=username,
            password=password
        ).first()

        if user:
            session["user_id"]=user.id
            flash("Welcome back","success")
            return redirect("/dashboard")

        flash("Invalid credentials","error")

    return render_template("login.html")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]
        confirm=request.form["confirm_password"]

        if password!=confirm:
            flash("Passwords do not match","error")
            return redirect("/register")

        existing=User.query.filter_by(
            username=username
        ).first()

        if existing:
            flash("Username already exists","error")
            return redirect("/register")

        user=User(
            username=username,
            password=hash_password(password)
        )

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully","success")
        return redirect("/login")

    return render_template("register.html")

@app.route("/dashboard",methods=["GET","POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user=User.query.get(session["user_id"])

    if request.method=="POST":
        service=request.form["service"]
        date=request.form["date"]

        count=Appointment.query.filter_by(
            appointment_date=date,
            status="Booked"
        ).count()

        token=count+1

        appointment=Appointment(
            service=service,
            appointment_date=date,
            token_number=token,
            user_id=session["user_id"]
        )

        db.session.add(appointment)
        db.session.commit()

        flash(
            f"Appointment booked • Token #{token}",
            "success"
        )

        return redirect("/dashboard")

    appointments=Appointment.query.filter_by(
        user_id=session["user_id"]
    ).order_by(
        Appointment.created_at.desc()
    ).all()

    total=len(appointments)

    active=len([
        a for a in appointments
        if a.status=="Booked"
    ])

    cancelled=len([
        a for a in appointments
        if a.status=="Cancelled"
    ])

    today=datetime.now().strftime("%Y-%m-%d")

    today_bookings=Appointment.query.filter_by(
        appointment_date=today,
        status="Booked"
    ).count()

    load=load_status(today_bookings)

    appointment_data=[]

    for a in appointments:
        position=max(a.token_number-1,0)
        wait=position*15

        appointment_data.append({
            "id":a.id,
            "service":a.service,
            "date":a.appointment_date,
            "token":a.token_number,
            "status":a.status,
            "position":position,
            "wait":wait
        })

    return render_template(
        "dashboard.html",
        user=user,
        appointments=appointment_data,
        total=total,
        active=active,
        cancelled=cancelled,
        load=load
    )

@app.route("/cancel/<int:id>")
def cancel(id):
    if "user_id" not in session:
        return redirect("/login")

    appointment=Appointment.query.get_or_404(id)

    if appointment.user_id!=session["user_id"]:
        return redirect("/dashboard")

    appointment.status="Cancelled"
    db.session.commit()

    flash("Appointment cancelled","error")
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out","success")
    return redirect("/login")

if __name__=="__main__":
    app.run(debug=True)