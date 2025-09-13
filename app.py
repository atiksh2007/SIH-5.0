import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from models import db, Student, Teacher, Subject, Attendance, AccessLog
from helpers import decode_base64_image, get_face_encoding_from_pil, serialize_encoding, deserialize_encoding, compare_encodings
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
import io, csv

BASE_DIR = os.path.abspath(os.path.dirname(_file_))
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')

app = Flask(_name_)
app.config['SECRET_KEY'] = 'dev-secret-change-me'   # change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize DB and default teacher
@app.before_first_request
def create_db():
    db.create_all()
    if not Teacher.query.first():
        t = Teacher(email='teacher@example.com', name='Default Teacher', password_hash=generate_password_hash('password'))
        db.session.add(t)
        db.session.commit()

@app.route('/')
def home():
    return redirect(url_for('student_login'))

@app.route('/student/login')
def student_login():
    # simple static page; in prototype you might render template
    return "Use the frontend prototype (student login page)."

@app.route('/teacher/login')
def teacher_login():
    return "Use the frontend prototype (teacher login page)."

# Student dashboard route (placeholder)
@app.route('/student/dashboard/<student_id>')
def student_dashboard(student_id):
    student = Student.query.filter_by(student_id=student_id).first_or_404()
    return f"Student dashboard for {student.name} ({student.student_id})"

# API: face login (receives base64 image data)
@app.route('/api/face_login', methods=['POST'])
def api_face_login():
    data = request.json
    img_data = data.get('image')
    if not img_data:
        return jsonify({'success': False, 'msg': 'No image provided'}), 400

    pil = decode_base64_image(img_data)
    enc = get_face_encoding_from_pil(pil)
    if enc is None:
        return jsonify({'success': False, 'msg': 'Could not detect face in image'}), 400

    # find matching student
    candidates = Student.query.all()
    for s in candidates:
        if s.face_encoding:
            stored = deserialize_encoding(s.face_encoding)
            if compare_encodings(enc, stored):
                # mark attendance for today
                today = date.today()
                exists = Attendance.query.filter_by(student_id=s.id, date=today).first()
                if not exists:
                    att = Attendance(student_id=s.id, subject_id=None, date=today, status='Present', method='Face')
                    db.session.add(att)
                    db.session.commit()
                return jsonify({'success': True, 'student_id': s.student_id, 'name': s.name, 'msg': 'Attendance marked'})
    return jsonify({'success': False, 'msg': 'No match found'}), 404

# API: attendance summary for student (simple)
@app.route('/api/attendance_summary/<student_id>')
def api_attendance_summary(student_id):
    s = Student.query.filter_by(student_id=student_id).first_or_404()
    records = Attendance.query.filter_by(student_id=s.id).all()
    from collections import defaultdict
    months = defaultdict(lambda: {'present':0, 'total':0})
    for r in records:
        m = r.date.strftime("%Y-%m")
        months[m]['total'] += 1
        if r.status == 'Present':
            months[m]['present'] += 1
    items = sorted(months.items())
    labels = [k for k,v in items]
    values = [ (v['present']*100//v['total']) if v['total']>0 else 0 for k,v in items ]
    return jsonify({'labels': labels, 'values': values})

# Teacher dashboard route (placeholder)
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if not session.get('teacher'):
        return redirect(url_for('teacher_login'))
    students = Student.query.order_by(Student.name).all()
    return f"Teacher dashboard: {len(students)} students"

@app.route('/teacher/do_login', methods=['POST'])
def teacher_do_login():
    email = request.form.get('email')
    password = request.form.get('password')
    t = Teacher.query.filter_by(email=email).first()
    if t and check_password_hash(t.password_hash, password):
        session['teacher'] = t.id
        return redirect(url_for('teacher_dashboard'))
    return "Invalid credentials", 401

# API: mark present (manual)
@app.route('/api/mark_present', methods=['POST'])
def api_mark_present():
    data = request.json
    student_id = data.get('student_id')
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return jsonify({'success': False, 'msg': 'Student not found'}), 404
    today = date.today()
    exists = Attendance.query.filter_by(student_id=student.id, date=today).first()
    if exists:
        return jsonify({'success': False, 'msg': 'Already marked today'}), 400
    teacher_id = session.get('teacher')
    att = Attendance(student_id=student.id, date=today, status='Present', method='Manual', marked_by=teacher_id)
    db.session.add(att)
    db.session.commit()
    return jsonify({'success': True, 'msg': 'Marked present'})

# API: add student
@app.route('/api/add_student', methods=['POST'])
def api_add_student():
    data = request.form
    sid = data.get('student_id')
    name = data.get('name')
    student_class = data.get('student_class')
    if Student.query.filter_by(student_id=sid).first():
        return "Student exists", 400
    s = Student(student_id=sid, name=name, student_class=student_class)
    if 'photo' in request.files:
        f = request.files['photo']
        save_path = os.path.join(BASE_DIR, 'data', f.filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        f.save(save_path)
        s.photo_path = save_path
        try:
            pil = Image.open(save_path)
            enc = get_face_encoding_from_pil(pil)
            if enc is not None:
                s.face_encoding = serialize_encoding(enc)
        except Exception as e:
            print("Encoding error", e)
    db.session.add(s)
    db.session.commit()
    return redirect(url_for('teacher_dashboard'))

# Export CSV
@app.route('/teacher/export_attendance')
def teacher_export_attendance():
    if not session.get('teacher'):
        return redirect(url_for('teacher_login'))
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['student_id', 'student_name', 'date', 'status', 'method'])
    rows = db.session.query(Attendance, Student).join(Student, Attendance.student_id==Student.id).all()
    for att, st in rows:
        cw.writerow([st.student_id, st.name, att.date.isoformat(), att.status, att.method])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, download_name='attendance_export.csv', as_attachment=True)

# Dev helper: create sample students
@app.route('/dev/create_sample')
def dev_create_sample():
    if not Student.query.filter_by(student_id='S101').first():
        s1 = Student(student_id='S101', name='Ali Khan', student_class='CSE-2')
        s2 = Student(student_id='S102', name='Meera Sharma', student_class='CSE-2')
        s3 = Student(student_id='S103', name='Rohit Verma', student_class='CSE-2')
        db.session.add_all([s1,s2,s3])
        db.session.commit()
    return "Sample students created"

@app.route('/teacher/logout')
def teacher_logout():
    session.pop('teacher', None)
    return redirect(url_for('teacher_login'))

if _name_ == '_main_':
    app.run(debug=True)