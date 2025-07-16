import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import urandom
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app: Flask = Flask(__name__)
app.secret_key = urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    region = db.Column(db.String(100), nullable=False)
    yield_per_sqm = db.Column(db.Float, nullable=False)
    market_price_per_kg = db.Column(db.Float, nullable=False)
    cost_seedlings = db.Column(db.Float, nullable=False)
    cost_labor = db.Column(db.Float, nullable=False)
    cost_fertilizer = db.Column(db.Float, nullable=False)
    cost_water = db.Column(db.Float, nullable=False)
    cost_pest = db.Column(db.Float, nullable=False)
    cost_maintenance = db.Column(db.Float, nullable=False)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("გთხოვთ გაიარეთ ავტორიზაცია", "warning")
            return redirect(url_for("login"))

        user = User.query.get(user_id)
        if not user or not user.is_admin:
            flash("თქვენ არ გაქვთ წვდომა ამ გვერდზე", "danger")
            return redirect(url_for("home"))

        return f(*args, **kwargs)
    return decorated_function


with app.app_context():
    db.create_all()

@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        flash("შენ არ გაქვს წვდომა ამ გვერდზე", "danger")
        return redirect(url_for('login'))

    users = User.query.all()  # ყველა მომხმარებლის წამოღება DB-დან
    return render_template('admin_users.html', users=users)

categories = {
    "ხილი": {
        "ვაშლი": {"price": 3.5, "desc": "ახალი მოწეული გურული ვაშლი.", "img": "apple.png"},
        "ატამი": {"price": 4.0, "desc": "მარტვილის რბილი ატამი.", "img": "atami.png"},
        "მსხალი": {"price": 3.0, "desc": "თეთრი მსხალი კახეთიდან.", "img": "msxali.png"}
    },
    "ბოსტნეული": {
        "კარტოფილი": {"price": 2.0, "desc": "ქართული კარტოფილი ჩაქვიდან.", "img": "kartofili.png"},
        "პამიდორი": {"price": 3.2, "desc": "ბაღის პამიდორი.", "img": "pamidori.png"}
    },
    "ღვინო და ვაზი": {
        "საფერავი": {"price": 35.5, "desc": "ქვევრის ღვინო გურნადან.", "img": "saperavi.png"}
    },
    "მარცვლეული": {
        "სიმინდი": {"price": 1.5, "desc": "იმერული სიმინდი.", "img": "simindi.png"}
    },
    "ძროხის პროდუქტები": {
        "რძე": {"price": 2.8, "desc": "ბაღდათის რძე.", "img": "rdze.png"}
    },
    "ბიო პროდუქტები": {
        "თაფლი": {"price": 10.0, "desc": "ტყის თაფლი.", "img": "tapli.png"}
    }
}


@app.route('/form1', endpoint='form1')
def form1():
    return render_template('form1.html')

@app.route('/add_crop', methods=['GET', 'POST'])
def add_crop():
    if not session.get('is_admin'):
        flash("თქვენ არ გაქვთ წვდომა ამ გვერდზე", "danger")
        return redirect(url_for('profile'))


    if request.method == 'POST':
        try:
            new_crop = Crop(
                name=request.form['name'],
                region=request.form['region'],
                yield_per_sqm=float(request.form['yield_per_sqm']),
                market_price_per_kg=float(request.form['market_price']),
                cost_seedlings=float(request.form['cost_seedlings']),
                cost_labor=float(request.form['cost_labor']),
                cost_fertilizer=float(request.form['cost_fertilizer']),
                cost_water=float(request.form['cost_water']),
                cost_pest=float(request.form['cost_pest']),
                cost_maintenance=float(request.form['cost_maintenance'])
            )
            db.session.add(new_crop)
            db.session.commit()
            flash("კულტურა წარმატებით დაემატა", "success")
        except Exception as e:
            flash(f"შეცდომა: {e}", "danger")

    return render_template('add_crop.html')

@app.route('/admin/crops')
def admin_crops():
    if not session.get('is_admin'):
        flash("არ გაქვთ წვდომა", "danger")
        return redirect(url_for('profile'))

    crops_list = Crop.query.all()
    return render_template('admin_crops.html', crops=crops_list)

@app.route("/rare", endpoint='rare_page')
def rare():
    return render_template("info pet and.html")

@app.route('/category/<category>')
def show_category(category):
    products = categories.get(category)
    if not products:
        return "კატეგორია ვერ მოიძებნა", 404
    return render_template("category.html", category=category, products=products)


@app.route('/category/<category>/<name>')
def product_detail(category, name):
    products = categories.get(category)
    if not products or name not in products:
        return "პროდუქტი ვერ მოიძებნა", 404
    return render_template("product_detail.html", name=name, product=products[name])


@app.route('/very1', methods=['GET', 'POST'], endpoint='index')
def index():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash("გთხოვთ შეიყვანოთ ელფოსტა", "error")
            return redirect(url_for('index'))

        verification_code = random.randint(100001, 999999)
        session['verification_code'] = verification_code
        session['email'] = email

        subject = "ვერიფიკაციის კოდი"
        body = f"თქვენი ვერიფიკაციის კოდია: {verification_code}"

        sender_email = "shota.cholokava17@gmail.com"
        password = "vgdc lvtc iozy jwni"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, email, msg.as_string())
            flash("ვერიფიკაციის კოდი გაიგზავნა ელფოსტაზე", "success")
            return redirect(url_for('verify1'))
        except Exception as e:
            flash(f"შეცდომა გაგზავნისას: {e}", "error")
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/verify1')
def verify1():
    return render_template('verify.html')


@app.route('/verify', methods=['POST'])
def verify():
    code = request.form.get('code')
    try:
        if int(code) == session.get('verification_code'):
            user_data = session.get('registration_data')
            if user_data:
                new_user = User(
                    name=user_data['name'],
                    surname=user_data['surname'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    state=user_data['state'],  #
                    city=user_data['city']     #

                )
                db.session.add(new_user)
                db.session.commit()

                # გასუფთავდეს session
                session.pop('registration_data', None)
                session.pop('verification_code', None)

                flash("Ვერიფიკაცია წარმატებით დასრულდა. რეგისტრაცია დასრულდა!", "success")
                return redirect(url_for('login'))
            else:
                flash("მონაცემები არ მოიძებნა", "error")
        else:
            flash("არასწორი ვერიფიკაციის კოდი", "error")
    except ValueError:
        flash("კოდი უნდა იყოს რიცხვი", "error")

    return render_template('verify.html')

@app.route('/paroli', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            # აქ შეიძლება პაროლის აღდგენა გაგზავნა (მაგალითად სარანდომო პაროლი)
            new_password = str(random.randint(100000, 999999))
            hashed_password = generate_password_hash(new_password)
            user.password_hash = hashed_password
            db.session.commit()

            # გაგზავნა ელფოსტით
            subject = "ახალი პაროლი"
            body = f"თქვენი ახალი პაროლია: {new_password}"

            sender_email = "shota.cholokava17@gmail.com"
            password = "vgdc lvtc iozy jwni"

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, password)
                    server.sendmail(sender_email, email, msg.as_string())
                flash("ახალი პაროლი გაიგზავნა ელფოსტაზე", "success")
            except Exception as e:
                flash(f"შეცდომა გაგზავნისას: {e}", "error")
        else:
            flash("ელფოსტა არ არის რეგისტრირებული", "danger")

    return render_template('forgot.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("გთხოვთ გაიარეთ ავტორიზაცია", "warning")
        return redirect(url_for('login', next=request.path))

    user = User.query.get(user_id)
    if not user:
        flash("მომხმარებელი ვერ მოიძებნა", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        state = request.form.get('state')
        city = request.form.get('city')
        zip_code = request.form.get('zip_code')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # აუცილებელია რეგიონის შერჩევა
        if not state:
            flash("გთხოვ, აირჩიე რეგიონი", "danger")
            return redirect(url_for('profile'))

        # ვამოწმებ პაროლს თუ შეიყვანა
        if new_password:
            if new_password != confirm_password:
                flash("პაროლები არ ემთხვევა", "danger")
                return redirect(url_for('profile'))
            user.password_hash = generate_password_hash(new_password)

        admin_code = request.form.get('admin_code')
        if admin_code == 'mindori1232':
            session['is_admin'] = True
            user.is_admin = True
            flash("თქვენ გახდით ადმინისტრატორი!", "success")


        # პროფილის სხვა ველების განახლება
        user.name = name
        user.surname = surname
        user.state = state
        user.city = city
        user.zip_code = zip_code

        db.session.commit()
        session['state'] = user.state

        flash("პროფილი წარმატებით განახლდა", "success")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)
 

@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.name
            session['state'] = user.state
            session['is_admin'] = user.is_admin

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('form1'))

        else:
            flash("არასწორი ელფოსტა ან პაროლი", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("შედი ან დარეგისტრირდი რათა ისარგებლო ყველა ფუნქციით", "info")
    return redirect(url_for('login'))



@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    result = None
    state = session.get('state')

    if not state:
        flash("გთხოვთ დალოგინდით ან დარეგისტრირდეთ", "warning")
        return redirect(url_for('login', next=request.path))

    allowed_crops = Crop.query.filter_by(region=state).all()
    crops_dict = {
        crop.name: {
            "yield_per_sqm": crop.yield_per_sqm,
            "market_price_per_kg": crop.market_price_per_kg,
            "costs": {
                "ნერგების ფასი": crop.cost_seedlings,
                "შრომა": crop.cost_labor,
                "სასუქი": crop.cost_fertilizer,
                "წყალი": crop.cost_water,
                "მავნებლების კონტროლი": crop.cost_pest,
                "მოვლა და პატრონობა": crop.cost_maintenance
            }
        } for crop in allowed_crops
    }

    if request.method == 'POST':
        try:
            length = float(request.form.get('length') or 0)
            width = float(request.form.get('width') or 0)
            area = float(request.form.get('area') or 0)
            crop_name = request.form.get('crop')

            if crop_name not in crops_dict:
                flash("გთხოვთ აირჩიოთ რეგიონისთვის შესაბამისი კულტურა", "error")
                return redirect(url_for('analyze'))

            total_area = length * width if length and width else area
            crop_data = crops_dict[crop_name]
            yield_total = total_area * crop_data['yield_per_sqm']
            income = yield_total * crop_data['market_price_per_kg']
            cost_details = {k: v * total_area for k, v in crop_data['costs'].items()}
            total_costs = sum(cost_details.values())
            profit = income - total_costs

            result = {
                'area': round(total_area, 2),
                'yield': round(yield_total, 2),
                'income': round(income, 2),
                'costs': round(total_costs, 2),
                'profit': round(profit, 2),
                'cost_details': {k: round(v, 2) for k, v in cost_details.items()}
            }

        except Exception as e:
            flash(f"შეცდომა: {e}", "error")

    return render_template('analyze.html', crops=crops_dict, result=result)


comments = []
comment_counter = 1
@app.route('/forum', methods=['GET', 'POST'])
def forum():
    global comment_counter

    success = False
    if request.method == 'POST':
        username = request.form['username']
        text = request.form['comment']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        comments.append({
            'id': comment_counter,
            'username': username,
            'text': text,
            'timestamp': timestamp,
            'reply': None
        })
        comment_counter += 1
        success = True

    is_admin = session.get('is_admin', False)
    return render_template('forum.html', comments=comments, success=success, is_admin=is_admin)

@app.route('/admin/edit_crop/<int:crop_id>', methods=['GET', 'POST'])
@admin_required
def edit_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)

    if request.method == 'POST':
        try:
            crop.name = request.form['name']
            crop.region = request.form['region']
            crop.yield_per_sqm = float(request.form['yield_per_sqm'])
            crop.market_price_per_kg = float(request.form['market_price'])
            crop.cost_seedlings = float(request.form['cost_seedlings'])
            crop.cost_labor = float(request.form['cost_labor'])
            crop.cost_fertilizer = float(request.form['cost_fertilizer'])
            crop.cost_water = float(request.form['cost_water'])
            crop.cost_pest = float(request.form['cost_pest'])
            crop.cost_maintenance = float(request.form['cost_maintenance'])

            db.session.commit()
            flash("კულტურა განახლდა", "success")
            return redirect(url_for('admin_crops'))
        except Exception as e:
            flash(f"შეცდომა: {e}", "danger")

    return render_template('edit_crop.html', crop=crop)

@app.route('/admin/delete_crop/<int:crop_id>', methods=['POST'])
@admin_required
def delete_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    db.session.delete(crop)
    db.session.commit()
    flash("კულტურა წაიშალა", "info")
    return redirect(url_for('admin_crops'))




@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if not session.get('is_admin'):
        return "Unauthorized", 403
    global comments
    comments = [c for c in comments if c['id'] != comment_id]
    return redirect(url_for('forum'))

@app.route('/reply_comment/<int:comment_id>', methods=['POST'])
def reply_comment(comment_id):
    if not session.get('is_admin'):
        return "Unauthorized", 403
    reply_text = request.form.get('reply_text')
    for comment in comments:
        if comment['id'] == comment_id:
            comment['reply'] = reply_text
            break
    return redirect(url_for('forum'))



@app.route("/rare", endpoint='rare')
def rare():
    return render_template("info pet and.html")


@app.route("/lesse", endpoint='lesse')
def lesse():
    return render_template("online.html")

@app.route("/")
def firt():
    return render_template("form1.html")



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        password = request.form.get('password')
        state = request.form.get('state')
        city = request.form.get('city')
        confirm_password = request.form.get('confirm_password')

        # გადაამოწმე იმეილი
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("ელფოსტა უკვე რეგისტრირებულია", "danger")
            return render_template('register form.html')

        if password != confirm_password:
            flash("პაროლები არ ემთხვევა", "danger")
            return render_template('register form.html')

        # ჰეშირებული პაროლი
        hashed_password = generate_password_hash(password)

        # ვამზადებთ ვერიფიკაციის კოდს და სესიის მონაცემებს
        verification_code = random.randint(100001, 999999)
        session['verification_code'] = verification_code
        session['registration_data'] = {
            'name': name,
            'surname': surname,
            'email': email,
            'password_hash': hashed_password,
            'state': state,   
            'city': city      
        }

        # ვუგზავნით კოდს
        subject = "ვერიფიკაციის კოდი"
        body = f"თქვენი ვერიფიკაციის კოდია: {verification_code}"
        sender_email = "shota.cholokava17@gmail.com"
        password_smtp = "vgdc lvtc iozy jwni"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password_smtp)
                server.sendmail(sender_email, email, msg.as_string())
            flash("ვერიფიკაციის კოდი გაიგზავნა ელფოსტაზე", "success")
            return redirect(url_for('verify1'))
        except Exception as e:
            flash(f"შეცდომა გაგზავნისას: {e}", "danger")
            return render_template('register form.html')

    return render_template('register form.html')



@app.route('/archevani', endpoint='archevani')
def page():
    return render_template('data.html')


@app.route('/about', endpoint='about')
def about():
    return render_template('about.html')


@app.route("/KALATA", endpoint='view_cart')
def view_cart():
    cart_items = session.get("cart", [])
    total = sum(item["price"] * item["quantity"] for item in cart_items)
    return render_template("cart.html", cart=cart_items, total=total)


@app.route('/home', endpoint='home')
def home():
    return render_template('form1.html')


if __name__ == '__main__':
    app.run(debug=True)
