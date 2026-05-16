from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Admin, Doctor, Patient, Appointment, Prescription, Billing
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hospital_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ============================
# INITIALIZATION & SEEDING
# ============================
with app.app_context():
    db.create_all()
    # Create default admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin = Admin(username='admin', password=hashed_pw)
        db.session.add(admin)
        db.session.commit()
        print("Default admin created (admin / admin123)")

    if not Doctor.query.filter_by(username='doctor').first():
        hashed_pw = generate_password_hash('doctor123', method='pbkdf2:sha256')
        doc = Doctor(name='John Doe', specialization='Cardiology', phone='1234567890', email='john@example.com', username='doctor', password=hashed_pw)
        db.session.add(doc)
        db.session.commit()
        print("Default doctor created (doctor / doctor123)")
        
    if not Patient.query.filter_by(username='patient').first():
        hashed_pw = generate_password_hash('patient123', method='pbkdf2:sha256')
        pat = Patient(name='Alice Smith', age=30, gender='Female', phone='0987654321', username='patient', password=hashed_pw)
        db.session.add(pat)
        db.session.commit()
        print("Default patient created (patient / patient123)")

# ============================
# HELPER DECORATORS OR CHECKS
# ============================
def check_auth(role):
    if 'role' not in session or session['role'] != role:
        flash("Unauthorized access. Please login first.", "danger")
        if role == 'admin': return redirect(url_for('login_admin'))
        if role == 'doctor': return redirect(url_for('login_doctor'))
        if role == 'patient': return redirect(url_for('login_patient'))
    return None

# ============================
# ROUTES
# ============================

@app.route('/')
def index():
    if 'role' in session:
        if session['role'] == 'admin': return redirect(url_for('dashboard_admin'))
        elif session['role'] == 'doctor': return redirect(url_for('dashboard_doctor'))
        elif session['role'] == 'patient': return redirect(url_for('dashboard_patient'))
    return redirect(url_for('login_admin'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

# --- LOGIN ROUTES ---
@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form['username']).first()
        if admin and check_password_hash(admin.password, request.form['password']):
            session['user_id'] = admin.id
            session['username'] = admin.username
            session['role'] = 'admin'
            flash("Admin logged in successfully", "success")
            return redirect(url_for('dashboard_admin'))
        flash("Invalid credentials", "danger")
    return render_template('login_admin.html')

@app.route('/login/doctor', methods=['GET', 'POST'])
def login_doctor():
    if request.method == 'POST':
        doctor = Doctor.query.filter_by(username=request.form['username']).first()
        if doctor and check_password_hash(doctor.password, request.form['password']):
            session['user_id'] = doctor.id
            session['name'] = doctor.name
            session['role'] = 'doctor'
            flash("Doctor logged in successfully", "success")
            return redirect(url_for('dashboard_doctor'))
        flash("Invalid credentials", "danger")
    return render_template('login_doctor.html')

@app.route('/login/patient', methods=['GET', 'POST'])
def login_patient():
    if request.method == 'POST':
        patient = Patient.query.filter_by(username=request.form['username']).first()
        if patient and check_password_hash(patient.password, request.form['password']):
            session['user_id'] = patient.id
            session['name'] = patient.name
            session['role'] = 'patient'
            flash("Patient logged in successfully", "success")
            return redirect(url_for('dashboard_patient'))
        flash("Invalid credentials", "danger")
    return render_template('login_patient.html')


# --- ADMIN ROUTES ---
@app.route('/admin/dashboard')
def dashboard_admin():
    auth = check_auth('admin')
    if auth: return auth
    
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    today = datetime.now().strftime('%Y-%m-%d')
    total_appointments = Appointment.query.filter_by(date=today).count()
    
    paid_bills = Billing.query.filter_by(status='Paid').all()
    total_revenue = sum(b.amount for b in paid_bills)
    
    pending_bills = Billing.query.filter_by(status='Pending').all()
    
    return render_template('dashboard_admin.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           total_revenue=total_revenue,
                           pending_bills=pending_bills)

@app.route('/admin/doctors', methods=['GET', 'POST'])
def admin_doctors():
    auth = check_auth('admin')
    if auth: return auth
    
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_doc = Doctor(
            name=request.form['name'],
            specialization=request.form['specialization'],
            phone=request.form['phone'],
            email=request.form['email'],
            username=request.form['username'],
            password=hashed_pw
        )
        try:
            db.session.add(new_doc)
            db.session.commit()
            flash("Doctor added successfully!", "success")
        except Exception as e:
            flash("Error adding doctor. Username or Email might exist.", "danger")
            db.session.rollback()
        return redirect(url_for('admin_doctors'))

    search = request.args.get('search')
    if search:
        doctors = Doctor.query.filter((Doctor.name.contains(search)) | (Doctor.specialization.contains(search))).all()
    else:
        doctors = Doctor.query.all()
    return render_template('admin_doctors.html', doctors=doctors)

@app.route('/admin/doctors/edit/<int:id>', methods=['POST'])
def edit_doctor(id):
    auth = check_auth('admin')
    if auth: return auth
    doctor = Doctor.query.get_or_404(id)
    doctor.name = request.form['name']
    doctor.specialization = request.form['specialization']
    doctor.phone = request.form['phone']
    doctor.email = request.form['email']
    db.session.commit()
    flash("Doctor updated successfully!", "success")
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctors/delete/<int:id>', methods=['POST'])
def delete_doctor(id):
    auth = check_auth('admin')
    if auth: return auth
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor deleted.", "info")
    return redirect(url_for('admin_doctors'))


@app.route('/admin/patients', methods=['GET', 'POST'])
def admin_patients():
    auth = check_auth('admin')
    if auth: return auth
    
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_pt = Patient(
            name=request.form['name'],
            age=int(request.form['age']),
            gender=request.form['gender'],
            phone=request.form['phone'],
            username=request.form['username'],
            password=hashed_pw
        )
        try:
            db.session.add(new_pt)
            db.session.commit()
            flash("Patient added successfully!", "success")
        except Exception as e:
            flash("Error adding patient. Username might exist.", "danger")
            db.session.rollback()
        return redirect(url_for('admin_patients'))

    search = request.args.get('search')
    if search:
        patients = Patient.query.filter((Patient.name.contains(search)) | (Patient.phone.contains(search))).all()
    else:
        patients = Patient.query.all()
    return render_template('admin_patients.html', patients=patients)

@app.route('/admin/patients/edit/<int:id>', methods=['POST'])
def edit_patient(id):
    auth = check_auth('admin')
    if auth: return auth
    pt = Patient.query.get_or_404(id)
    pt.name = request.form['name']
    pt.age = int(request.form['age'])
    pt.gender = request.form['gender']
    pt.phone = request.form['phone']
    db.session.commit()
    flash("Patient updated successfully!", "success")
    return redirect(url_for('admin_patients'))

@app.route('/admin/patients/delete/<int:id>', methods=['POST'])
def delete_patient(id):
    auth = check_auth('admin')
    if auth: return auth
    pt = Patient.query.get_or_404(id)
    db.session.delete(pt)
    db.session.commit()
    flash("Patient deleted.", "info")
    return redirect(url_for('admin_patients'))


@app.route('/admin/appointments', methods=['GET', 'POST'])
def admin_appointments():
    auth = check_auth('admin')
    if auth: return auth
    
    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']
        doctor_id = request.form['doctor_id']
        
        # Check double booking for the doctor
        existing = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time, status='Scheduled').first()
        if existing:
            flash("Doctor is already booked for this time slot. Please choose another time.", "danger")
        else:
            appt = Appointment(
                patient_id=request.form['patient_id'],
                doctor_id=doctor_id,
                date=date,
                time=time
            )
            db.session.add(appt)
            db.session.commit()
            flash("Appointment scheduled successfully!", "success")
        return redirect(url_for('admin_appointments'))

    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    return render_template('admin_appointments.html', appointments=appointments, patients=patients, doctors=doctors)


@app.route('/admin/billing', methods=['GET', 'POST'])
def admin_billing():
    auth = check_auth('admin')
    if auth: return auth
    
    if request.method == 'POST':
        bill = Billing(
            patient_id=request.form['patient_id'],
            amount=float(request.form['amount']),
            date=datetime.now().strftime('%Y-%m-%d %H:%M')
        )
        db.session.add(bill)
        db.session.commit()
        flash("Bill generated successfully!", "success")
        return redirect(url_for('admin_billing'))

    bills = Billing.query.order_by(Billing.id.desc()).all()
    patients = Patient.query.all()
    return render_template('admin_billing.html', bills=bills, patients=patients)

@app.route('/admin/billing/mark_paid/<int:id>', methods=['POST'])
def mark_bill_paid(id):
    auth = check_auth('admin')
    if auth: return auth
    bill = Billing.query.get_or_404(id)
    bill.status = 'Paid'
    db.session.commit()
    flash("Bill marked as Paid.", "success")
    return redirect(url_for('admin_billing'))


# --- DOCTOR ROUTES ---
@app.route('/doctor/dashboard')
def dashboard_doctor():
    auth = check_auth('doctor')
    if auth: return auth
    doctor_id = session['user_id']
    doctor = Doctor.query.get(doctor_id)
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).order_by(Appointment.date.asc(), Appointment.time.asc()).all()
    return render_template('dashboard_doctor.html', assignments=appointments, appointments=appointments, doctor=doctor)

@app.route('/doctor/prescription', methods=['POST'])
def add_prescription():
    auth = check_auth('doctor')
    if auth: return auth
    
    doctor_id = session['user_id']
    appt_id = request.form['appointment_id']
    
    pres = Prescription(
        patient_id=request.form['patient_id'],
        doctor_id=doctor_id,
        diagnosis=request.form['diagnosis'],
        medicines=request.form['medicines'],
        date=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    db.session.add(pres)
    
    # Mark appointment as completed
    appt = Appointment.query.get(appt_id)
    if appt:
        appt.status = 'Completed'
        
    db.session.commit()
    flash("Prescription saved and appointment marked as completed.", "success")
    return redirect(url_for('dashboard_doctor'))


# --- PATIENT ROUTES ---
@app.route('/patient/dashboard')
def dashboard_patient():
    auth = check_auth('patient')
    if auth: return auth
    patient_id = session['user_id']
    patient = Patient.query.get(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).order_by(Prescription.id.desc()).all()
    bills = Billing.query.filter_by(patient_id=patient_id).order_by(Billing.id.desc()).all()
    
    return render_template('dashboard_patient.html', patient=patient, appointments=appointments, prescriptions=prescriptions, bills=bills)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
