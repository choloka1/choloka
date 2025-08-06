import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import requests


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB ინიციალიზაცია
db = SQLAlchemy(app)

# ========= მოდელები =========
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

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(200))  # ეს აუცილებელია, რადგან შენ HTML-ით აგზავნი subtitle-ს
    description = db.Column(db.Text)
    ticket = db.Column(db.String(100))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender = db.Column(db.String(50))  # 'user' ან 'admin'
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='messages')


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    text = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(10))  # 'user' or 'admin'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class RestoreRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    student_class = db.Column(db.String(10))
    age = db.Column(db.Integer)
    homeroom_teacher = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    subject_teacher = db.Column(db.String(100))
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ადმინის ავტორიზაციის დეკორატორი
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

# Routes

@app.route('/admin/reply_restore/<int:reg_id>', methods=['POST'])
@admin_required
def reply_restore(reg_id):
    reply_text = request.form.get('reply_text')
    registration = RestoreRegistration.query.get_or_404(reg_id)
    registration.reply = reply_text
    db.session.commit()
    flash("კომენტარი დაემატა", "success")
    return redirect(url_for('restore_list'))

@app.route('/admin/delete_restore/<int:reg_id>', methods=['POST'])
@admin_required
def delete_restore(reg_id):
    registration = RestoreRegistration.query.get_or_404(reg_id)
    db.session.delete(registration)
    db.session.commit()
    flash("რეგისტრაცია წაიშალა", "info")
    return redirect(url_for('restore_list'))



@app.route('/restore_list')
@admin_required
def restore_list():
    registrations = RestoreRegistration.query.order_by(RestoreRegistration.created_at.desc()).all()
    return render_template('restore_list.html', registrations=registrations)

@app.route('/restore_registration', methods=['GET', 'POST'])
def restore_registration():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        student_class = request.form.get('student_class')
        age = request.form.get('age')
        homeroom_teacher = request.form.get('homeroom_teacher')
        subject = request.form.get('subject')
        subject_teacher = request.form.get('subject_teacher')
        confirmed = request.form.get('confirmed') == 'on'

        if not confirmed:
            flash("გთხოვთ დაეთანხმოთ პირობებს", "danger")
            return redirect(url_for('restore_registration'))

        registration = RestoreRegistration(
            name=name,
            surname=surname,
            student_class=student_class,
            age=age,
            homeroom_teacher=homeroom_teacher,
            subject=subject,
            subject_teacher=subject_teacher,
            confirmed=confirmed
        )
        db.session.add(registration)
        db.session.commit()

        flash("განაცხადი წარმატებით გაიგზავნა", "success")
        return redirect(url_for('home'))

    return render_template('restore_form.html')



@app.route('/')
def home():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("home_page.html", posts=posts)


@app.route('/event')
def event():
    events = Event.query.all()
    return render_template('infov.html', events=events)

@app.route('/event/delete/<int:event_id>', methods=['POST'])
@admin_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('ივენთი წაიშალა წარმატებით', 'success')
    return redirect(url_for('events'))  # <-- შეცვალე შესაბამისი როუტის სახელით



@app.route('/event/add', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        subtitle = request.form.get('subtitle')  # დაამატე ეს
        description = request.form['description']
        ticket = request.form['ticket']

        new_event = Event(
            title=title,
            subtitle=subtitle,
            description=description,
            ticket=ticket
        )
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('event'))

    return render_template('add_event.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        state = request.form.get('state')
        city = request.form.get('city')

        #  1. reCAPTCHA შემოწმება
        #recaptcha_response = request.form.get('g-recaptcha-response')
        #secret_key = 'შეიყვანე_შენი_secret_key_აქ'  # შეავსე შენი reCAPTCHA საიდუმლო გასაღებით
        #verify_url = 'https://www.google.com/recaptcha/api/siteverify'

       # response = requests.post(verify_url, data={
            #'secret': secret_key,
           # 'response': recaptcha_response
       # })
        #result = response.json()

        #if not result.get('success'):
           # flash('გთხოვთ დაადასტურეთ, რომ არ ხართ რობოტი.', 'danger')
           # return render_template('register form.html')

        #  2. უკვე რეგისტრირებული ელფოსტა
        if User.query.filter_by(email=email).first():
            flash("ელფოსტა უკვე რეგისტრირებულია", "danger")
            return render_template('register form.html')

        #  3. პაროლების შედარება
        if password != confirm_password:
            flash("პაროლები არ ემთხვევა", "danger")
            return render_template('register form.html')

        hashed_password = generate_password_hash(password)

        #  4. კოდის გენერაცია
        verification_code = random.randint(100001, 999999)
        print(verification_code)

        #  5. სესიაში რეგისტრაციის მონაცემები
        session['verification_code'] = verification_code
        session['registration_data'] = {
            'name': name,
            'surname': surname,
            'email': email,
            'password_hash': hashed_password,
            'state': state,
            'city': city
        }

        #  6. ელფოსტის გაგზავნა
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


@app.route('/verify1')
def verify1():
    return render_template('verify.html')




@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    Message.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("მომხმარებელი წაიშალა", "info")
    return redirect(url_for('users'))




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
                    state=user_data['state'],
                    city=user_data['city']
                )
                db.session.add(new_user)
                db.session.commit()

                session.pop('registration_data', None)
                session.pop('verification_code', None)

                flash("ვერიფიკაცია წარმატებით დასრულდა. რეგისტრაცია დასრულდა!", "success")
                return redirect(url_for('login'))
            else:
                flash("მონაცემები არ მოიძებნა", "danger")
        else:
            flash("არასწორი ვერიფიკაციის კოდი", "danger")
    except ValueError:
        flash("კოდი უნდა იყოს რიცხვი", "danger")

    return render_template('verify.html')


@app.route('/login', methods=['GET', 'POST'])
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
            return redirect(next_page) if next_page else redirect(url_for('home_page'))
        else:
            flash("არასწორი ელფოსტა ან პაროლი", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            new_password = str(random.randint(100000, 999999))
            hashed_password = generate_password_hash(new_password)
            user.password_hash = hashed_password
            db.session.commit()

            subject = "ახალი პაროლი"
            body = f"თქვენი ახალი პაროლია: {new_password}"
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
                flash("ახალი პაროლი გაიგზავნა ელფოსტაზე", "success")
            except Exception as e:
                flash(f"შეცდომა გაგზავნისას: {e}", "danger")
        else:
            flash("ელფოსტა არ არის რეგისტრირებული", "danger")

    return render_template('forgot.html')


@app.route('/form1')
def home_page():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("home_page.html", posts=posts)



@app.route('/archevani')
def foa():
    return render_template('data.html')

@app.route('/saskolo')
def saskologo():
    return render_template('saskolo.html')

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


@app.route('/logout')
def logout():
    session.clear()
    flash("შედი ან დარეგისტრირდი რათა ისარგებლო ყველა ფუნქციით", "info")
    return redirect(url_for('login'))



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

        if not state:
            flash("გთხოვ, აირჩიე რეგიონი", "danger")
            return redirect(url_for('profile'))

        if new_password:
            if new_password != confirm_password:
                flash("პაროლები არ ემთხვევა", "danger")
                return redirect(url_for('profile'))
            user.password_hash = generate_password_hash(new_password)

        admin_code = request.form.get('admin_code')
        if admin_code == 'mindori123222':
            session['is_admin'] = True
            user.is_admin = True
            flash("თქვენ გახდით ადმინისტრატორი!", "success")

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


@app.route('/manage_posts', methods=['GET', 'POST'])
def manage_posts():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        image = request.files.get('image')
        image_url = ''
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_url = f"/static/uploads/{filename}"

        new_post = Post(title=title, content=content, image_url=image_url)
        db.session.add(new_post)
        db.session.commit()
        flash('პოსტი წარმატებით აიტვირთა!')
        return redirect(url_for('manage_posts'))

    return render_template('manage_posts.html')


@app.route("/post")
def post_list():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("post_list.html", posts=posts)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post_detail.html", post=post)



@app.route('/post/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if not session.get('is_admin'):
        flash("⛔ მხოლოდ ადმინს აქვს წვდომა.")
        return redirect(url_for('post_list'))

    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']

        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            post.image_url = f"/static/uploads/{filename}"

        try:
            db.session.commit()
            flash("✅ პოსტი წარმატებით განახლდა.")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ შეცდომა: {e}")

        return redirect(url_for('post_list'))

    return render_template('edit_post.html', post=post)

@app.route('/post/delete/<int:post_id>')
def delete_post(post_id):
    if not session.get('is_admin'):
        flash("⛔ მხოლოდ ადმინს აქვს წვდომა.")
        return redirect(url_for('post_list'))

    post = db.session.merge(Post.query.get_or_404(post_id))  # სწორი სესიაში დაბრუნება
    db.session.delete(post)
    db.session.commit()
    flash('🗑️ პოსტი წაიშალა.')
    return redirect(url_for('post_list'))


@app.route('/create_survey')
@admin_required
def create_survey():
    return render_template('create_survey.html')


@app.route('/admin/')
@admin_required
def admin():
    return render_template('admin_dashboard.html')

@app.route('/users', endpoint='users')
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users_list.html', users=users)

@app.route('/adminchat')
@admin_required
def admin_chat_list():
    users = User.query.all()
    users_with_unread = []

    for user in users:
        # ვპოულობთ ბოლო შეტყობინებას ამ მომხმარებელზე
        last_msg = Message.query.filter_by(user_id=user.id).order_by(Message.timestamp.desc()).first()

        # თუ ბოლო შეტყობინება არის 'user'-ისგან, ნიშნავს რომ ადმინს არ უპასუხია
        has_unread = last_msg and last_msg.sender == 'user'

        # ვქმნით განახლებულ მომხმარებლის ჩანაწერს
        users_with_unread.append({
            'id': user.id,
            'name': user.name,
            'surname': user.surname,
            'email': user.email,
            'has_unread': has_unread
        })

    return render_template('admin_chat_list.html', users=users_with_unread)


@app.route('/admin/chat/<int:user_id>', methods=['GET', 'POST'])
def admin_chat_with_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        message_text = request.form['message']
        if message_text.strip():
            new_message = Message(
                user_id=user.id,             # მომხმარებლის ID, ვისაც ეგზავნება
                sender='admin',              # ვინ აგზავნის — ამ შემთხვევაში admin
                text=message_text
            )
            db.session.add(new_message)
            db.session.commit()
            return redirect(url_for('admin_chat_with_user', user_id=user.id))

    # ამოიღე ყველა შეტყობინება ამ მომხმარებელთან
    messages = Message.query.filter_by(user_id=user.id).order_by(Message.timestamp.asc()).all()

    return render_template('admin_chat_detail.html', user=user, messages=messages)


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        flash("გთხოვთ გაიაროთ ავტორიზაცია", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    messages = Message.query.filter_by(user_id=user.id).order_by(Message.timestamp).all()

    if request.method == 'POST':
        text = request.form.get('text')
        if text:
            msg = Message(user_id=user.id, sender='user', text=text)
            db.session.add(msg)
            db.session.commit()
            flash("შეტყობინება გაიგზავნა", "success")
            return redirect(url_for('chat'))

    return render_template('chat_user.html', user=user, messages=messages)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

