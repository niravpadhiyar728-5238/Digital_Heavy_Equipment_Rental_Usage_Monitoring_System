from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime, date
import random
import string

app = Flask(__name__)
app.secret_key = 'equipment-rental-secure-2026-v2.1'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rental.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# DATABASE MODELS
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empnumber = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    userid = db.Column(db.String(100), unique=True)
    loginpassword = db.Column(db.String(50))
    salary = db.Column(db.Float, nullable=False)
    workinghoursday = db.Column(db.Integer, default=8)
    workingdaysmonth = db.Column(db.Integer, default=26)
    salaryperhour = db.Column(db.Float)
    overtimepercentage = db.Column(db.Float, default=50.0)
    overtimerateperhour = db.Column(db.Float)

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100))
    number = db.Column(db.String(50), unique=True)
    year = db.Column(db.Integer)
    capacityton = db.Column(db.Float)
    uniqueno = db.Column(db.String(50), unique=True)

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    companyname = db.Column(db.String(100), nullable=False)
    companyaddress = db.Column(db.String(200))
    siteaddress = db.Column(db.String(200))
    equipmentid = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    wonumber = db.Column(db.String(50), unique=True, nullable=False)
    wodate = db.Column(db.Date)
    startdate = db.Column(db.Date)
    enddate = db.Column(db.Date)
    perioddays = db.Column(db.Integer)
    ratetype = db.Column(db.String(10), default='hourly')
    rateperhour = db.Column(db.Float)
    totalhoursday = db.Column(db.Float, default=8.0)
    shifthours = db.Column(db.Float, default=8.0)
    numshifts = db.Column(db.Integer, default=1)
    daysmonth = db.Column(db.Integer, default=26)
    totalamount = db.Column(db.Float)

class Logsheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lognumber = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date)
    shiftstart = db.Column(db.String(10))
    shiftend = db.Column(db.String(10))
    lunchtime = db.Column(db.String(10), default='13:00')
    lunchminutes = db.Column(db.Integer, default=60)
    totalshifttime = db.Column(db.String(10))
    hourmeterstart = db.Column(db.Float, default=0)
    hourmeterend = db.Column(db.Float, default=0)
    diffhourmeter = db.Column(db.Float)
    overtimehours = db.Column(db.Float, default=0)
    breakdown = db.Column(db.String(100))
    empoperatorid = db.Column(db.Integer, db.ForeignKey('employee.id'))
    empoperatornumber = db.Column(db.String(50))
    empoperatorname = db.Column(db.String(100))
    emprate = db.Column(db.Float)
    diesel = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text)
    woid = db.Column(db.Integer, db.ForeignKey('work_order.id'))

# HELPER FUNCTIONS
def time_to_minutes(time_str):
    if not time_str: return 0
    try:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    except:
        return 0

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'userid' not in session:
            flash('Please login first!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def create_default_admin():
    """Auto-create admin user on first run"""
    if not Employee.query.filter_by(role='Admin').first():
        admin = Employee(
            empnumber='ADMIN001',
            name='System Administrator',
            role='Admin',
            salary=50000.0,
            workinghoursday=8,
            workingdaysmonth=26,
            overtimepercentage=50.0
        )
        admin.userid = 'admin'
        admin.loginpassword = 'admin123'
        admin.salaryperhour = admin.salary / (admin.workingdaysmonth * admin.workinghoursday)
        admin.overtimerateperhour = admin.salaryperhour * (1 + admin.overtimepercentage/100)
        db.session.add(admin)
        db.session.commit()
        print("✅ ADMIN CREATED: Username: 'admin' | Password: 'admin123'")

# ROUTES
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        emp = Employee.query.filter_by(userid=userid, loginpassword=password).first()
        if emp:
            session['userid'] = userid
            session['empname'] = emp.name
            session['role'] = emp.role
            flash(f'✅ Welcome {emp.name}!', 'success')
            return redirect(url_for('index'))
        flash('❌ Invalid credentials! Try: admin / admin123', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    stats = {
        'employees': Employee.query.count(),
        'equipment': Equipment.query.count(),
        'workorders': WorkOrder.query.count(),
        'logsheets': Logsheet.query.count()
    }
    return render_template('index.html', stats=stats)

@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    if request.method == 'POST':
        emp = Employee(
            empnumber=request.form['empnumber'],
            name=request.form['name'],
            role=request.form['role'],
            salary=float(request.form['salary']),
            workinghoursday=int(request.form.get('workinghoursday', 8)),
            workingdaysmonth=int(request.form.get('workingdaysmonth', 26)),
            overtimepercentage=float(request.form.get('overtimepercentage', 50))
        )
        emp.userid = emp.name.lower().replace(' ', '.') + str(random.randint(100,999))
        emp.loginpassword = emp.role[:4].upper() + '-' + emp.empnumber[-4:]
        emp.salaryperhour = emp.salary / (emp.workingdaysmonth * emp.workinghoursday)
        emp.overtimerateperhour = emp.salaryperhour * (1 + emp.overtimepercentage/100)
        db.session.add(emp)
        db.session.commit()
        flash(f'✅ Employee created! Rate: ₹{emp.salaryperhour:.2f}/hr', 'success')
        return redirect(url_for('employees'))
    emps = Employee.query.all()
    return render_template('employees.html', employees=emps)

@app.route('/equipment', methods=['GET', 'POST'])
@login_required
def equipment():
    if request.method == 'POST':
        uniqueno = f"{request.form['number'].upper()}{request.form['company'][:3].upper()}{request.form['year']}{int(float(request.form['capacityton']))}"
        if Equipment.query.filter_by(uniqueno=uniqueno).first():
            flash('❌ Equipment Unique No already exists!', 'danger')
        else:
            eq = Equipment(
                company=request.form['company'].title(),
                number=request.form['number'].upper(),
                year=int(request.form['year']),
                capacityton=float(request.form['capacityton']),
                uniqueno=uniqueno
            )
            db.session.add(eq)
            db.session.commit()
            flash(f'✅ Equipment added! Unique No: {uniqueno}', 'success')
    eqs = Equipment.query.all()
    return render_template('equipment.html', equipment=eqs)

@app.route('/workorders', methods=['GET', 'POST'])
@login_required
def workorders():
    if request.method == 'POST':
        wo = WorkOrder(
            companyname=request.form['companyname'],
            companyaddress=request.form['companyaddress'],
            siteaddress=request.form['siteaddress'],
            equipmentid=int(request.form.get('equipmentid')) if request.form.get('equipmentid') else None,
            wonumber=request.form['wonumber'],
            wodate=datetime.strptime(request.form['wodate'], '%Y-%m-%d').date(),
            startdate=datetime.strptime(request.form['startdate'], '%Y-%m-%d').date(),
            enddate=datetime.strptime(request.form['enddate'], '%Y-%m-%d').date(),
            ratetype=request.form['ratetype'],
            rateperhour=float(request.form['rateperhour']),
            shifthours=float(request.form.get('shifthours', 8)),
            numshifts=int(request.form.get('numshifts', 1)),
            daysmonth=int(request.form.get('daysmonth', 26))
        )
        wo.perioddays = (wo.enddate - wo.startdate).days + 1
        if wo.ratetype == 'monthly':
            wo.totalamount = wo.rateperhour * wo.daysmonth
        else:
            wo.totalamount = wo.rateperhour * wo.shifthours * wo.numshifts * wo.perioddays
        db.session.add(wo)
        db.session.commit()
        flash(f'✅ Work Order {wo.wonumber} created! Total: ₹{wo.totalamount:,.0f}', 'success')
        return redirect(url_for('workorders'))
    
    current_date = date.today()
    wos = WorkOrder.query.all()
    eqs = Equipment.query.all()
    return render_template('workorders.html', workorders=wos, equipment=eqs, current_date=current_date, logs=Logsheet.query.all())

@app.route('/logsheets', methods=['GET', 'POST'])
@login_required
def logsheets():
    if request.method == 'POST':
        ls = Logsheet(
            lognumber=request.form['lognumber'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            shiftstart=request.form.get('shiftstart', ''),
            shiftend=request.form.get('shiftend', ''),
            lunchminutes=int(request.form.get('lunchminutes', 60)),
            hourmeterstart=float(request.form.get('hourmeterstart', 0)),
            hourmeterend=float(request.form.get('hourmeterend', 0)),
            overtimehours=float(request.form.get('overtimehours', 0)),
            empoperatorid=int(request.form.get('empoperatorid')) if request.form.get('empoperatorid') else None,
            empoperatornumber=request.form.get('empoperatornumber', ''),
            empoperatorname=request.form.get('empoperatorname', ''),
            emprate=float(request.form.get('emprate', 0)),
            diesel=float(request.form.get('diesel', 0)),
            breakdown=request.form.get('breakdown', ''),
            remarks=request.form.get('remarks', ''),
            woid=int(request.form.get('woid')) if request.form.get('woid') else None
        )
        start_min = time_to_minutes(ls.shiftstart)
        end_min = time_to_minutes(ls.shiftend)
        raw_total = end_min - start_min
        if raw_total < 0: raw_total += 24*60
        net_total = raw_total - ls.lunchminutes
        hours, mins = divmod(net_total, 60)
        ls.totalshifttime = f"{hours:02d}:{mins:02d}"
        ls.diffhourmeter = ls.hourmeterend - ls.hourmeterstart
        db.session.add(ls)
        db.session.commit()
        flash(f'✅ Logsheet {ls.lognumber} saved!', 'success')
        return redirect(url_for('logsheets'))
    
    logs = Logsheet.query.all()
    emps = Employee.query.all()
    wos = WorkOrder.query.all()
    return render_template('logsheets.html', logsheets=logs, employees=emps, workorders=wos)

@app.route('/report/<int:woid>')
@login_required
def report(woid):
    wo = WorkOrder.query.get_or_404(woid)
    logs = Logsheet.query.filter_by(woid=woid).order_by(Logsheet.date).all()
    equipment = Equipment.query.get(wo.equipmentid) if wo.equipmentid else None
    
    if not logs:
        flash(f'No logsheets for WO {wo.wonumber}. Add logs first!', 'info')
        return redirect(url_for('logsheets'))
    
    total_shifthours = sum(time_to_minutes(log.totalshifttime)/60 for log in logs)
    total_hourmeter = sum(log.diffhourmeter or 0 for log in logs)
    total_diesel = sum(log.diesel or 0 for log in logs)
    total_othours = sum(log.overtimehours or 0 for log in logs)
    
    return render_template('report.html', workorder=wo, logs=logs, equipment=equipment, totals={
        'shifthours': total_shifthours,
        'hourmeter': total_hourmeter,
        'diesel': total_diesel,
        'othours': total_othours
    })

@app.route('/summary')
@login_required
def summary():
    return render_template('summary.html', 
                         employees=Employee.query.all(),
                         equipment=Equipment.query.all(),
                         workorders=WorkOrder.query.all(),
                         logsheets=Logsheet.query.all()[-10:])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_admin()  # 🔥 AUTO-CREATE ADMIN USER
    print("🚀 Equipment Rental App - http://localhost:5000")
    print("🔑 ADMIN LOGIN: Username: 'admin' | Password: 'admin123'")
    app.run(debug=True, port=5000, host='0.0.0.0')



"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime, date
import random
import string

app = Flask(__name__)
app.secret_key = 'equipment-rental-secure-2026-v2.1'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rental.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# DATABASE MODELS (ENHANCED)
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empnumber = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    userid = db.Column(db.String(100), unique=True)
    loginpassword = db.Column(db.String(50))
    salary = db.Column(db.Float, nullable=False)
    workinghoursday = db.Column(db.Integer, default=8)
    workingdaysmonth = db.Column(db.Integer, default=26)
    salaryperhour = db.Column(db.Float)
    overtimepercentage = db.Column(db.Float, default=50.0)
    overtimerateperhour = db.Column(db.Float)

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100))
    number = db.Column(db.String(50), unique=True)
    year = db.Column(db.Integer)
    capacityton = db.Column(db.Float)
    uniqueno = db.Column(db.String(50), unique=True)
    workorders = db.relationship('WorkOrder', backref='equipment', lazy=True)

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    companyname = db.Column(db.String(100), nullable=False)
    companyaddress = db.Column(db.String(200))
    siteaddress = db.Column(db.String(200))
    equipmentid = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    wonumber = db.Column(db.String(50), unique=True, nullable=False)
    wodate = db.Column(db.Date)
    startdate = db.Column(db.Date)
    enddate = db.Column(db.Date)
    perioddays = db.Column(db.Integer)
    ratetype = db.Column(db.String(10), default='hourly')  # NEW: hourly/monthly
    rateperhour = db.Column(db.Float)
    totalhoursday = db.Column(db.Float, default=8.0)
    shifthours = db.Column(db.Float, default=8.0)
    numshifts = db.Column(db.Integer, default=1)
    daysmonth = db.Column(db.Integer, default=26)
    totalamount = db.Column(db.Float)
    logsheets = db.relationship('Logsheet', backref='workorder', lazy=True)

class Logsheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lognumber = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date)
    shiftstart = db.Column(db.String(10))
    shiftend = db.Column(db.String(10))
    lunchtime = db.Column(db.String(10), default='13:00')
    lunchminutes = db.Column(db.Integer, default=60)
    totalshifttime = db.Column(db.String(10))
    hourmeterstart = db.Column(db.Float, default=0)
    hourmeterend = db.Column(db.Float, default=0)
    diffhourmeter = db.Column(db.Float)
    overtimehours = db.Column(db.Float, default=0)
    breakdown = db.Column(db.String(100))
    empoperatorid = db.Column(db.Integer, db.ForeignKey('employee.id'))
    empoperatornumber = db.Column(db.String(50))
    empoperatorname = db.Column(db.String(100))
    emprate = db.Column(db.Float)
    diesel = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text)
    woid = db.Column(db.Integer, db.ForeignKey('work_order.id'))

# HELPER FUNCTIONS
def time_to_minutes(time_str):
    if not time_str: return 0
    try:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    except:
        return 0

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'userid' not in session:
            flash('Please login first!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ROUTES
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        emp = Employee.query.filter_by(userid=userid, loginpassword=password).first()
        if emp:
            session['userid'] = userid
            session['empname'] = emp.name
            session['role'] = emp.role
            flash(f'Welcome {emp.name}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    stats = {
        'employees': Employee.query.count(),
        'equipment': Equipment.query.count(),
        'workorders': WorkOrder.query.count(),
        'logsheets': Logsheet.query.count()
    }
    return render_template('index.html', stats=stats)

@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    if request.method == 'POST':
        emp = Employee(
            empnumber=request.form['empnumber'],
            name=request.form['name'],
            role=request.form['role'],
            salary=float(request.form['salary']),
            workinghoursday=int(request.form.get('workinghoursday', 8)),
            workingdaysmonth=int(request.form.get('workingdaysmonth', 26)),
            overtimepercentage=float(request.form.get('overtimepercentage', 50))
        )
        emp.userid = emp.name.lower().replace(' ', '.') + str(random.randint(100,999))
        emp.loginpassword = emp.role[:4].upper() + '-' + emp.empnumber[-4:]
        emp.salaryperhour = emp.salary / (emp.workingdaysmonth * emp.workinghoursday)
        emp.overtimerateperhour = emp.salaryperhour * (1 + emp.overtimepercentage/100)
        db.session.add(emp)
        db.session.commit()
        flash(f'Employee created! Rate: ₹{emp.salaryperhour:.2f}/hr', 'success')
        return redirect(url_for('employees'))
    emps = Employee.query.all()
    return render_template('employees.html', employees=emps)

@app.route('/equipment', methods=['GET', 'POST'])
@login_required
def equipment():
    if request.method == 'POST':
        uniqueno = f"{request.form['number'].upper()}{request.form['company'][:3].upper()}{request.form['year']}{int(float(request.form['capacityton']))}"
        if Equipment.query.filter_by(uniqueno=uniqueno).first():
            flash('Equipment Unique No already exists!', 'danger')
        else:
            eq = Equipment(
                company=request.form['company'].title(),
                number=request.form['number'].upper(),
                year=int(request.form['year']),
                capacityton=float(request.form['capacityton']),
                uniqueno=uniqueno
            )
            db.session.add(eq)
            db.session.commit()
            flash(f'Equipment added! Unique No: {uniqueno}', 'success')
    eqs = Equipment.query.all()
    return render_template('equipment.html', equipment=eqs)

@app.route('/workorders', methods=['GET', 'POST'])
@login_required
def workorders():
    if request.method == 'POST':
        wo = WorkOrder(
            companyname=request.form['companyname'],
            companyaddress=request.form['companyaddress'],
            siteaddress=request.form['siteaddress'],
            equipmentid=int(request.form.get('equipmentid')) if request.form.get('equipmentid') else None,
            wonumber=request.form['wonumber'],
            wodate=datetime.strptime(request.form['wodate'], '%Y-%m-%d').date(),
            startdate=datetime.strptime(request.form['startdate'], '%Y-%m-%d').date(),
            enddate=datetime.strptime(request.form['enddate'], '%Y-%m-%d').date(),
            ratetype=request.form['ratetype'],
            rateperhour=float(request.form['rateperhour']),
            shifthours=float(request.form.get('shifthours', 8)),
            numshifts=int(request.form.get('numshifts', 1)),
            daysmonth=int(request.form.get('daysmonth', 26))
        )
        wo.perioddays = (wo.enddate - wo.startdate).days + 1
        if wo.ratetype == 'monthly':
            wo.totalamount = wo.rateperhour * wo.daysmonth
        else:
            wo.totalamount = wo.rateperhour * wo.shifthours * wo.numshifts * wo.perioddays
        db.session.add(wo)
        db.session.commit()
        flash(f'Work Order {wo.wonumber} created! Total: ₹{wo.totalamount:,.0f}', 'success')
        return redirect(url_for('workorders'))
    
    wos = WorkOrder.query.all()
    eqs = Equipment.query.all()
    return render_template('workorders.html', workorders=wos, equipment=eqs)

@app.route('/logsheets', methods=['GET', 'POST'])
@login_required
def logsheets():
    if request.method == 'POST':
        ls = Logsheet(
            lognumber=request.form['lognumber'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            shiftstart=request.form.get('shiftstart', ''),
            shiftend=request.form.get('shiftend', ''),
            lunchminutes=int(request.form.get('lunchminutes', 60)),
            hourmeterstart=float(request.form.get('hourmeterstart', 0)),
            hourmeterend=float(request.form.get('hourmeterend', 0)),
            overtimehours=float(request.form.get('overtimehours', 0)),
            empoperatorid=int(request.form.get('empoperatorid')) if request.form.get('empoperatorid') else None,
            empoperatornumber=request.form.get('empoperatornumber', ''),
            empoperatorname=request.form.get('empoperatorname', ''),
            emprate=float(request.form.get('emprate', 0)),
            diesel=float(request.form.get('diesel', 0)),
            breakdown=request.form.get('breakdown', ''),
            remarks=request.form.get('remarks', ''),
            woid=int(request.form.get('woid')) if request.form.get('woid') else None
        )
        # Auto calculations
        start_min = time_to_minutes(ls.shiftstart)
        end_min = time_to_minutes(ls.shiftend)
        raw_total = end_min - start_min
        if raw_total < 0: raw_total += 24*60
        net_total = raw_total - ls.lunchminutes
        hours, mins = divmod(net_total, 60)
        ls.totalshifttime = f"{hours:02d}:{mins:02d}"
        ls.diffhourmeter = ls.hourmeterend - ls.hourmeterstart
        db.session.add(ls)
        db.session.commit()
        flash(f'Logsheet {ls.lognumber} saved!', 'success')
        return redirect(url_for('logsheets'))
    
    logs = Logsheet.query.all()
    emps = Employee.query.all()
    wos = WorkOrder.query.all()
    return render_template('logsheets.html', logsheets=logs, employees=emps, workorders=wos)

@app.route('/report/<int:woid>')
@login_required
def report(woid):
    wo = WorkOrder.query.get_or_404(woid)
    logs = Logsheet.query.filter_by(woid=woid).order_by(Logsheet.date).all()
    
    if not logs:
        flash(f'No logsheets for WO {wo.wonumber}. Add logs first!', 'info')
        return redirect(url_for('logsheets', woid=woid))
    
    # Calculate totals
    total_shifthours = sum(time_to_minutes(log.totalshifttime)/60 for log in logs)
    total_hourmeter = sum(log.diffhourmeter or 0 for log in logs)
    total_diesel = sum(log.diesel or 0 for log in logs)
    total_othours = sum(log.overtimehours or 0 for log in logs)
    
    return render_template('report.html', workorder=wo, logs=logs, totals={
        'shifthours': total_shifthours,
        'hourmeter': total_hourmeter,
        'diesel': total_diesel,
        'othours': total_othours
    })

@app.route('/summary')
@login_required
def summary():
    return render_template('summary.html', 
                         employees=Employee.query.all(),
                         equipment=Equipment.query.all(),
                         workorders=WorkOrder.query.all(),
                         logsheets=Logsheet.query.all()[-10:])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Equipment Rental App running on http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')
"""