from app.extensions import db


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default="admin")
    is_owner = db.Column(db.Integer, nullable=False, default=0)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.Text, nullable=False)
    student_id = db.Column(db.Text, nullable=False)
    subjects = db.Column(db.Text, nullable=False)
    school_key = db.Column(db.Text, nullable=False, default="")


class StudentsSheetMap(db.Model):
    __tablename__ = "students_sheet_map"

    school_key = db.Column(db.Text, primary_key=True)
    sheet_student_id = db.Column(db.Integer, primary_key=True)
    student_row_id = db.Column(db.Integer, nullable=False, unique=True)


__all__ = ["Admin", "Student", "StudentsSheetMap"]
