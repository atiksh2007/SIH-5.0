from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Student(db.Model):
    _tablename_ = "students"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(64), unique=True, nullable=False)  # e.g. roll number
    name = db.Column(db.String(128), nullable=False)
    student_class = db.Column(db.String(64))
    email = db.Column(db.String(128))
    phone = db.Column(db.String(32))
    photo_path = db.Column(db.String(256))
    face_encoding = db.Column(db.LargeBinary)  # store raw bytes (pickle) or JSON

class Teacher(db.Model):
    _tablename_ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128))
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(32), default="teacher")

class Subject(db.Model):
    _tablename_ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    class_name = db.Column(db.String(64))

class Attendance(db.Model):
    _tablename_ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(16), nullable=False)  # Present/Absent/Late
    marked_by = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    method = db.Column(db.String(32), default="Face")  # Face / Manual
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AccessLog(db.Model):
    _tablename_ = "access_logs"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    location = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(32))  # Granted/Denied