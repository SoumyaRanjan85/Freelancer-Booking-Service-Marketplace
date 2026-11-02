import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from config import Config
from database import get_db, init_db, seed_db, SKILLS_TAXONOMY
from utils.auth import hash_password, verify_password, login_required, role_required, get_current_user
from utils.validation import is_valid_email, is_valid_password, save_uploaded_file

app = Flask(__name__)
app.config.from_object(Config)

# Auto-initialize database if not existing
with app.app_context():
    if not os.path.exists(Config.DATABASE_PATH):
        seed_db()

@app.before_request
def load_logged_in_user():
    g.user = get_current_user()

@app.context_processor
def inject_user_and_taxonomy():
    return dict(current_user=g.user, skills_taxonomy=SKILLS_TAXONOMY)

@app.route('/api/skills')
def api_skills():
    query = request.args.get('q', '').strip().lower()
    matches = []
    for cat, skills in SKILLS_TAXONOMY.items():
        for skill in skills:
            if not query or query in skill.lower() or query in cat.lower():
                matches.append({'skill': skill, 'category': cat})
    return jsonify({'skills': matches[:30], 'total': len(matches)})

# -------------------------------------------------------------
# Authentication Routes (Module 1)
# -------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'client').strip().lower()

        if not full_name or not email or not password:
            flash("All required fields must be filled.", "danger")
            return render_template('auth/register.html')

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template('auth/register.html')

        if not is_valid_password(password):
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register.html')

        if role not in ['client', 'freelancer']:
            role = 'client'

        db = get_db()
        existing = db.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            db.close()
            flash("An account with that email already exists. Please log in.", "warning")
            return redirect(url_for('login'))

        pwd_hash = hash_password(password)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO users (full_name, email, password_hash, role, avatar_url)
            VALUES (?, ?, ?, ?, ?)
        """, (full_name, email, pwd_hash, role, "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150"))
        user_id = cursor.lastrowid

        # If freelancer, initialize profile
        if role == 'freelancer':
            cursor.execute("""
                INSERT INTO freelancer_profiles (user_id, headline, skills, category, experience, bio, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, "Freelance Professional", "Communication, Project Management", "Development", 1, "Welcome to my profile! I am ready to collaborate on custom projects and fixed-price bookings.", 1000.0))

        db.commit()
        db.close()

        # Log user in
        session['user_id'] = user_id
        session['full_name'] = full_name
        session['email'] = email
        session['role'] = role
        session['avatar_url'] = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150"

        flash(f"Welcome to FreelanceConnect, {full_name}!", "success")
        if role == 'freelancer':
            return redirect(url_for('edit_profile'))
        return redirect(url_for('dashboard'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if not user or not verify_password(password, user['password_hash']):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('auth/login.html')

        if user['status'] == 'suspended':
            flash("Your account has been suspended by administration. Please contact support.", "danger")
            return render_template('auth/login.html')

        session['user_id'] = user['user_id']
        session['full_name'] = user['full_name']
        session['email'] = user['email']
        session['role'] = user['role']
        session['avatar_url'] = user['avatar_url']

        flash(f"Welcome back, {user['full_name']}!", "success")
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for('index'))

# -------------------------------------------------------------
# Marketplace & Discovery Routes (Module 2 & 3)
# -------------------------------------------------------------

@app.route('/')
def index():
    db = get_db()
    # Featured freelancers (12+ profiles covering multiple domains)
    featured_freelancers = db.execute("""
        SELECT u.user_id, u.full_name, u.avatar_url, p.headline, p.skills, p.category, 
               p.experience, p.hourly_rate, p.availability, p.rating_avg, p.rating_count
        FROM users u
        JOIN freelancer_profiles p ON u.user_id = p.user_id
        WHERE u.status = 'active'
        ORDER BY p.rating_avg DESC, p.experience DESC
        LIMIT 14
    """).fetchall()

    # Popular fixed services (14+ service packages covering multiple domains)
    popular_services = db.execute("""
        SELECT s.*, u.full_name as freelancer_name, u.avatar_url
        FROM services s
        JOIN users u ON s.freelancer_id = u.user_id
        WHERE s.status = 'Active' AND u.status = 'active'
        ORDER BY s.service_id ASC
        LIMIT 14
    """).fetchall()

    # Client reviews & testimonials (10+ verified reviews)
    client_reviews = db.execute("""
        SELECT r.*, uc.full_name as client_name, uc.avatar_url as client_avatar,
               uf.full_name as freelancer_name, uf.avatar_url as freelancer_avatar,
               s.title as service_title
        FROM reviews r
        JOIN users uc ON r.client_id = uc.user_id
        JOIN users uf ON r.freelancer_id = uf.user_id
        LEFT JOIN bookings b ON r.booking_id = b.booking_id
        LEFT JOIN services s ON b.service_id = s.service_id
        ORDER BY r.review_id DESC
        LIMIT 12
    """).fetchall()

    # Category definitions with icon and description
    categories_list = [
        {"name": "AI & Data Science", "icon": "fa-brain", "color": "#8b5cf6", "desc": "LLMs, RAG, PyTorch & Deep Learning", "count": 28, "starting": 1500},
        {"name": "Development", "icon": "fa-code", "color": "#4f46e5", "desc": "Python, Flask, React, Node & APIs", "count": 64, "starting": 1200},
        {"name": "Mobile Apps", "icon": "fa-mobile-screen", "color": "#0ea5e9", "desc": "Flutter, React Native & iOS/Android", "count": 35, "starting": 1400},
        {"name": "Design", "icon": "fa-pen-nib", "color": "#ec4899", "desc": "UI/UX, Figma & Brand Identity Kits", "count": 42, "starting": 999},
        {"name": "Writing", "icon": "fa-pen-fancy", "color": "#f59e0b", "desc": "Technical Documentation, SEO & Copy", "count": 31, "starting": 800},
        {"name": "DevOps & Cloud", "icon": "fa-server", "color": "#06b6d4", "desc": "Docker, Kubernetes, AWS & CI/CD", "count": 22, "starting": 1800},
        {"name": "Blockchain & Web3", "icon": "fa-cubes-stacked", "color": "#10b981", "desc": "Solidity, Smart Contracts & DApps", "count": 18, "starting": 2200},
        {"name": "Video & Motion", "icon": "fa-film", "color": "#f97316", "desc": "3D Blender, Motion Graphics & Visuals", "count": 26, "starting": 1100},
        {"name": "Cybersecurity", "icon": "fa-shield-halved", "color": "#ef4444", "desc": "Penetration Testing & Security Audits", "count": 16, "starting": 2000},
        {"name": "Business & Analytics", "icon": "fa-chart-line", "color": "#3b82f6", "desc": "Power BI, Financial Models & KPIs", "count": 24, "starting": 1200},
        {"name": "Game Development", "icon": "fa-gamepad", "color": "#a855f7", "desc": "Unity, Unreal Engine 5 & Shaders", "count": 15, "starting": 1600},
        {"name": "Digital Marketing", "icon": "fa-bullhorn", "color": "#14b8a6", "desc": "PPC, Technical SEO & Growth Funnels", "count": 39, "starting": 1000}
    ]

    # Hero visual showcase (12 rich cards representing platform achievements & deliveries)
    hero_showcase = [
        {"title": "Custom Fintech Multi-Vendor Architecture", "tag": "Model A Engagement", "badge": "Custom Project", "amount": "₹13,000", "days": "8 Days", "author": "Vikram Rao", "img": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=80", "highlight": "Agreed after 3 counterproposal versions with full audit trail"},
        {"title": "Eco-Artisanal Logo & Brand Identity Suite", "tag": "Model B Service", "badge": "Fixed Package", "amount": "₹1,499", "days": "3 Days", "author": "Ananya Sen", "img": "https://images.unsplash.com/photo-1626785774573-4b799315345d?w=600&auto=format&fit=crop&q=80", "highlight": "100% Vector EPS + Brand Book delivered ahead of schedule"},
        {"title": "Enterprise RAG Pipeline with LangChain", "tag": "AI Architecture", "badge": "Custom Project", "amount": "₹22,000", "days": "6 Days", "author": "Dr. Aakash Kulkarni", "img": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&auto=format&fit=crop&q=80", "highlight": "Hallucination-free document QA deployed with vector search"},
        {"title": "Cross-Platform Food Delivery Mobile App", "tag": "Mobile App", "badge": "Custom Project", "amount": "₹18,500", "days": "9 Days", "author": "Neha Patel", "img": "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=600&auto=format&fit=crop&q=80", "highlight": "60fps Flutter animation engine + SQLite offline order cache"},
        {"title": "Zero-Downtime AWS Kubernetes Multi-Cloud", "tag": "DevOps Pipeline", "badge": "Fixed Package", "amount": "₹2,999", "days": "3 Days", "author": "Marcus Vance", "img": "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=600&auto=format&fit=crop&q=80", "highlight": "GitHub Actions CI/CD pipeline with Terraform infrastructure"},
        {"title": "Audited DeFi Staking Smart Contract", "tag": "Web3 Protocol", "badge": "Fixed Package", "amount": "₹5,499", "days": "4 Days", "author": "Elena Rostova", "img": "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=600&auto=format&fit=crop&q=80", "highlight": "Zero post-launch vulnerabilities, 32% gas optimization achieved"},
        {"title": "Cinema 3D Commercial Product Reveal", "tag": "3D Motion", "badge": "Fixed Package", "amount": "₹4,499", "days": "5 Days", "author": "Tariq Mansoor", "img": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=80", "highlight": "Blender 3D fluid animation rendered in crystal 1080p 60fps"},
        {"title": "Fintech SOC2 Penetration Security Audit", "tag": "Cybersecurity", "badge": "Fixed Package", "amount": "₹5,999", "days": "4 Days", "author": "Sarah Jenkins", "img": "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&auto=format&fit=crop&q=80", "highlight": "Exhaustive OWASP assessment with prioritized POC remediations"},
        {"title": "Executive Board SaaS Financial Dashboard", "tag": "Business BI", "badge": "Fixed Package", "amount": "₹3,999", "days": "4 Days", "author": "Maya Lin", "img": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=80", "highlight": "Power BI model with automated DAX cohort retention analytics"},
        {"title": "Playable 3D Mobile Arena in Unity Engine", "tag": "Game Development", "badge": "Fixed Package", "amount": "₹6,999", "days": "6 Days", "author": "Kenji Takahashi", "img": "https://images.unsplash.com/photo-1552824722-ddab1374e622?w=600&auto=format&fit=crop&q=80", "highlight": "Complete C# gameplay mechanics, physics and compiled Android APK"},
        {"title": "High-ROAS Google Ads Acquisition Campaign", "tag": "Growth Marketing", "badge": "Fixed Package", "amount": "₹2,499", "days": "3 Days", "author": "Chloe Dubois", "img": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&auto=format&fit=crop&q=80", "highlight": "Reduced customer acquisition cost by 41% within 2 weeks"},
        {"title": "Developer API Architecture Reference Hub", "tag": "Technical Docs", "badge": "Fixed Package", "amount": "₹999", "days": "2 Days", "author": "Rohan Verma", "img": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=600&auto=format&fit=crop&q=80", "highlight": "100% Swagger/OpenAPI compliant interactive documentation"}
    ]

    db.close()
    return render_template(
        'index.html', 
        featured_freelancers=featured_freelancers, 
        popular_services=popular_services,
        client_reviews=client_reviews,
        categories_list=categories_list,
        hero_showcase=hero_showcase
    )


@app.route('/explore')
def explore_freelancers():
    query = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()
    min_exp = int(request.args.get('min_exp', 0))
    max_rate = float(request.args.get('max_rate', 5000))

    sql = """
        SELECT u.user_id, u.full_name, u.avatar_url, p.headline, p.skills, p.category, 
               p.experience, p.bio, p.hourly_rate, p.availability, p.rating_avg, p.rating_count
        FROM users u
        JOIN freelancer_profiles p ON u.user_id = p.user_id
        WHERE u.status = 'active'
    """
    params = []

    if query:
        sql += " AND (u.full_name LIKE ? OR p.skills LIKE ? OR p.headline LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term])

    if selected_category:
        sql += " AND p.category = ?"
        params.append(selected_category)

    if min_exp > 0:
        sql += " AND p.experience >= ?"
        params.append(min_exp)

    if max_rate:
        sql += " AND p.hourly_rate <= ?"
        params.append(max_rate)

    sql += " ORDER BY p.rating_avg DESC, p.rating_count DESC"

    db = get_db()
    freelancers = db.execute(sql, params).fetchall()
    db.close()

    return render_template(
        'explore.html', 
        freelancers=freelancers, 
        query=query, 
        selected_category=selected_category, 
        min_exp=min_exp, 
        max_rate=max_rate
    )


@app.route('/freelancer/<int:freelancer_id>')
def freelancer_profile(freelancer_id):
    db = get_db()
    freelancer = db.execute("""
        SELECT u.user_id, u.full_name, u.email, u.avatar_url, p.headline, p.skills, p.category, 
               p.experience, p.bio, p.portfolio_url, p.hourly_rate, p.availability, p.rating_avg, p.rating_count
        FROM users u
        JOIN freelancer_profiles p ON u.user_id = p.user_id
        WHERE u.user_id = ? AND u.status = 'active'
    """, (freelancer_id,)).fetchone()

    if not freelancer:
        db.close()
        flash("Freelancer profile not found.", "warning")
        return redirect(url_for('explore_freelancers'))

    # Published services by this freelancer
    services = db.execute("""
        SELECT * FROM services WHERE freelancer_id = ? AND status = 'Active' ORDER BY service_id ASC
    """, (freelancer_id,)).fetchall()

    # Verified reviews for this freelancer
    reviews = db.execute("""
        SELECT r.*, u.full_name as client_name, u.avatar_url as client_avatar
        FROM reviews r
        JOIN users u ON r.client_id = u.user_id
        WHERE r.freelancer_id = ?
        ORDER BY r.created_at DESC
    """, (freelancer_id,)).fetchall()

    db.close()
    return render_template('freelancer_profile.html', freelancer=freelancer, services=services, reviews=reviews)


@app.route('/services')
def browse_services():
    query = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()

    sql = """
        SELECT s.*, u.full_name as freelancer_name, u.avatar_url
        FROM services s
        JOIN users u ON s.freelancer_id = u.user_id
        WHERE s.status = 'Active' AND u.status = 'active'
    """
    params = []

    if query:
        sql += " AND (s.title LIKE ? OR s.description LIKE ? OR s.deliverables LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term])

    if selected_category:
        sql += " AND s.category = ?"
        params.append(selected_category)

    sql += " ORDER BY s.service_id ASC"

    db = get_db()
    services = db.execute(sql, params).fetchall()
    db.close()

    return render_template('services.html', services=services, query=query, selected_category=selected_category)


@app.route('/service/<int:service_id>')
def service_details(service_id):
    db = get_db()
    service = db.execute("""
        SELECT s.*, u.full_name as freelancer_name, u.avatar_url, p.headline, p.bio, p.rating_avg, p.rating_count
        FROM services s
        JOIN users u ON s.freelancer_id = u.user_id
        JOIN freelancer_profiles p ON u.user_id = p.user_id
        WHERE s.service_id = ? AND s.status = 'Active'
    """, (service_id,)).fetchone()
    db.close()

    if not service:
        flash("Service not found or is currently inactive.", "warning")
        return redirect(url_for('browse_services'))

    return render_template('service_details.html', service=service)

# -------------------------------------------------------------
# Model A: Consultation & Negotiation Workflow (Module 4 & 5)
# -------------------------------------------------------------

@app.route('/consultation/request/<int:freelancer_id>', methods=['GET', 'POST'])
@login_required
def request_consultation(freelancer_id):
    if session.get('role') != 'client':
        flash("Only registered clients can request consultation meetings.", "warning")
        return redirect(url_for('freelancer_profile', freelancer_id=freelancer_id))

    if session.get('user_id') == freelancer_id:
        flash("You cannot request a consultation with yourself.", "danger")
        return redirect(url_for('explore_freelancers'))

    db = get_db()
    freelancer = db.execute("""
        SELECT u.user_id, u.full_name, u.avatar_url, p.headline
        FROM users u
        JOIN freelancer_profiles p ON u.user_id = p.user_id
        WHERE u.user_id = ? AND u.status = 'active'
    """, (freelancer_id,)).fetchone()

    if not freelancer:
        db.close()
        flash("Freelancer not found.", "warning")
        return redirect(url_for('explore_freelancers'))

    if request.method == 'POST':
        request_title = request.form.get('request_title', '').strip()
        project_description = request.form.get('project_description', '').strip()
        preferred_datetime = request.form.get('preferred_datetime', '').strip()
        meeting_type = request.form.get('meeting_type', 'Online')
        notes = request.form.get('notes', '').strip()

        if not request_title or not project_description or not preferred_datetime:
            flash("Please fill in project title, description, and preferred meeting date/time.", "danger")
            db.close()
            return render_template('consultation.html', freelancer=freelancer, consultation=None)

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO consultations 
            (client_id, freelancer_id, request_title, project_description, preferred_datetime, meeting_type, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (session['user_id'], freelancer_id, request_title, project_description, preferred_datetime, meeting_type, notes))
        consultation_id = cursor.lastrowid
        db.commit()
        db.close()

        flash(f"Consultation request submitted to {freelancer['full_name']}! You can track status below.", "success")
        return redirect(url_for('consultation_details', consultation_id=consultation_id))

    db.close()
    return render_template('consultation.html', freelancer=freelancer, consultation=None)


@app.route('/consultation/<int:consultation_id>')
@login_required
def consultation_details(consultation_id):
    db = get_db()
    consultation = db.execute("""
        SELECT c.*, 
               uc.full_name as client_name, uc.email as client_email, uc.avatar_url as client_avatar,
               uf.full_name as freelancer_name, uf.email as freelancer_email, uf.avatar_url as freelancer_avatar
        FROM consultations c
        JOIN users uc ON c.client_id = uc.user_id
        JOIN users uf ON c.freelancer_id = uf.user_id
        WHERE c.consultation_id = ?
    """, (consultation_id,)).fetchone()
    db.close()

    if not consultation:
        flash("Consultation request not found.", "warning")
        return redirect(url_for('dashboard'))

    # Security check: Only involved parties or admin can view
    curr_id = session.get('user_id')
    curr_role = session.get('role')
    if curr_id not in [consultation['client_id'], consultation['freelancer_id']] and curr_role != 'admin':
        flash("Access denied. You are not a party in this consultation.", "danger")
        return redirect(url_for('dashboard'))

    return render_template('consultation.html', consultation=consultation, freelancer=None)


@app.route('/consultation/<int:consultation_id>/status', methods=['POST'])
@login_required
def update_consultation_status(consultation_id):
    db = get_db()
    consultation = db.execute("SELECT * FROM consultations WHERE consultation_id = ?", (consultation_id,)).fetchone()

    if not consultation:
        db.close()
        flash("Consultation not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    new_status = request.form.get('status')
    meeting_link = request.form.get('meeting_link', '').strip()
    notes = request.form.get('notes', '').strip()
    preferred_datetime = request.form.get('preferred_datetime', '').strip()

    # Freelancer acceptance/rejection/reschedule
    if curr_id == consultation['freelancer_id']:
        if new_status == 'Accepted':
            db.execute("""
                UPDATE consultations 
                SET status = 'Accepted', meeting_link = ?, notes = COALESCE(NULLIF(?, ''), notes)
                WHERE consultation_id = ?
            """, (meeting_link, notes, consultation_id))
            db.commit()
            flash("Consultation meeting confirmed! Link sent to client.", "success")
        elif new_status == 'Reschedule Requested':
            db.execute("""
                UPDATE consultations 
                SET status = 'Reschedule Requested', preferred_datetime = ?, notes = COALESCE(NULLIF(?, ''), notes)
                WHERE consultation_id = ?
            """, (preferred_datetime, notes, consultation_id))
            db.commit()
            flash("Reschedule request submitted to client.", "info")
        elif new_status == 'Rejected':
            db.execute("UPDATE consultations SET status = 'Rejected' WHERE consultation_id = ?", (consultation_id,))
            db.commit()
            flash("Consultation declined.", "warning")

    # Client accepting rescheduled datetime
    elif curr_id == consultation['client_id'] and new_status == 'Accepted':
        db.execute("UPDATE consultations SET status = 'Accepted' WHERE consultation_id = ?", (consultation_id,))
        db.commit()
        flash("Rescheduled meeting slot accepted!", "success")

    db.close()
    return redirect(url_for('consultation_details', consultation_id=consultation_id))


@app.route('/negotiation/<int:consultation_id>')
@login_required
def negotiation_room(consultation_id):
    db = get_db()
    consultation = db.execute("""
        SELECT c.*, 
               uc.full_name as client_name, uc.email as client_email,
               uf.full_name as freelancer_name, uf.email as freelancer_email
        FROM consultations c
        JOIN users uc ON c.client_id = uc.user_id
        JOIN users uf ON c.freelancer_id = uf.user_id
        WHERE c.consultation_id = ?
    """, (consultation_id,)).fetchone()

    if not consultation:
        db.close()
        flash("Consultation not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    curr_role = session.get('role')
    if curr_id not in [consultation['client_id'], consultation['freelancer_id']] and curr_role != 'admin':
        db.close()
        flash("Unauthorized access to negotiation workspace.", "danger")
        return redirect(url_for('dashboard'))

    # Fetch all proposals in order of version
    proposals = db.execute("""
        SELECT p.*, u.full_name as sender_name, u.role as sender_role
        FROM proposals p
        JOIN users u ON p.sender_id = u.user_id
        WHERE p.consultation_id = ?
        ORDER BY p.version ASC
    """, (consultation_id,)).fetchall()

    latest_proposal = proposals[-1] if proposals else None

    # Check if a custom booking exists for this consultation's accepted proposal
    custom_booking = None
    if latest_proposal and latest_proposal['status'] == 'Accepted':
        custom_booking = db.execute("""
            SELECT * FROM bookings WHERE proposal_id = ?
        """, (latest_proposal['proposal_id'],)).fetchone()

    db.close()
    return render_template(
        'negotiation.html', 
        consultation=consultation, 
        proposals=proposals, 
        latest_proposal=latest_proposal, 
        custom_booking=custom_booking
    )


@app.route('/negotiation/<int:consultation_id>/initial-proposal', methods=['POST'])
@login_required
def submit_initial_proposal(consultation_id):
    db = get_db()
    consultation = db.execute("SELECT * FROM consultations WHERE consultation_id = ?", (consultation_id,)).fetchone()

    if not consultation:
        db.close()
        flash("Consultation not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    if curr_id != consultation['freelancer_id']:
        db.close()
        flash("Only the assigned freelancer can submit the initial project proposal.", "danger")
        return redirect(url_for('negotiation_room', consultation_id=consultation_id))

    proposed_amount = float(request.form.get('proposed_amount', 0))
    delivery_days = int(request.form.get('delivery_days', 0))
    scope = request.form.get('scope', '').strip()
    message = request.form.get('message', '').strip()

    if proposed_amount <= 0 or delivery_days <= 0 or not scope:
        db.close()
        flash("Please provide a valid price, delivery timeline, and project scope.", "danger")
        return redirect(url_for('negotiation_room', consultation_id=consultation_id))

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO proposals 
        (consultation_id, sender_id, proposed_amount, delivery_days, scope, message, version, status)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'Pending')
    """, (consultation_id, curr_id, proposed_amount, delivery_days, scope, message))
    db.commit()
    db.close()

    flash("Initial project proposal submitted to client! Awaiting review or counteroffer.", "success")
    return redirect(url_for('negotiation_room', consultation_id=consultation_id))


@app.route('/proposal/<int:proposal_id>/counter', methods=['POST'])
@login_required
def submit_counterproposal(proposal_id):
    db = get_db()
    proposal = db.execute("""
        SELECT p.*, c.client_id, c.freelancer_id 
        FROM proposals p
        JOIN consultations c ON p.consultation_id = c.consultation_id
        WHERE p.proposal_id = ?
    """, (proposal_id,)).fetchone()

    if not proposal:
        db.close()
        flash("Proposal not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    if curr_id not in [proposal['client_id'], proposal['freelancer_id']]:
        db.close()
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard'))

    if proposal['status'] != 'Pending':
        db.close()
        flash("You can only counter a pending proposal.", "warning")
        return redirect(url_for('negotiation_room', consultation_id=proposal['consultation_id']))

    proposed_amount = float(request.form.get('proposed_amount', 0))
    delivery_days = int(request.form.get('delivery_days', 0))
    scope = request.form.get('scope', '').strip()
    message = request.form.get('message', '').strip()

    if proposed_amount <= 0 or delivery_days <= 0 or not scope:
        db.close()
        flash("Please provide valid counterproposal values.", "danger")
        return redirect(url_for('negotiation_room', consultation_id=proposal['consultation_id']))

    cursor = db.cursor()
    # Mark old proposal as Superseded
    cursor.execute("UPDATE proposals SET status = 'Superseded' WHERE proposal_id = ?", (proposal_id,))

    # Insert new version record
    new_version = proposal['version'] + 1
    cursor.execute("""
        INSERT INTO proposals 
        (consultation_id, sender_id, proposed_amount, delivery_days, scope, message, version, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (proposal['consultation_id'], curr_id, proposed_amount, delivery_days, scope, message, new_version))
    
    db.commit()
    db.close()

    flash(f"Counterproposal Version {new_version} submitted! Negotiation history updated.", "success")
    return redirect(url_for('negotiation_room', consultation_id=proposal['consultation_id']))


@app.route('/proposal/<int:proposal_id>/accept', methods=['POST'])
@login_required
def accept_proposal(proposal_id):
    db = get_db()
    proposal = db.execute("""
        SELECT p.*, c.client_id, c.freelancer_id, c.request_title
        FROM proposals p
        JOIN consultations c ON p.consultation_id = c.consultation_id
        WHERE p.proposal_id = ?
    """, (proposal_id,)).fetchone()

    if not proposal:
        db.close()
        flash("Proposal not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    # Can only accept if current user is the OTHER party (not the sender)
    if curr_id not in [proposal['client_id'], proposal['freelancer_id']]:
        db.close()
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard'))

    if curr_id == proposal['sender_id']:
        db.close()
        flash("You cannot accept your own proposal. Awaiting the other party to accept.", "warning")
        return redirect(url_for('negotiation_room', consultation_id=proposal['consultation_id']))

    cursor = db.cursor()
    # Mark this proposal as Accepted
    cursor.execute("UPDATE proposals SET status = 'Accepted' WHERE proposal_id = ?", (proposal_id,))
    # Mark previous pending proposals as Superseded
    cursor.execute("""
        UPDATE proposals SET status = 'Superseded' 
        WHERE consultation_id = ? AND proposal_id != ? AND status = 'Pending'
    """, (proposal['consultation_id'], proposal_id))
    # Mark consultation as Completed
    cursor.execute("UPDATE consultations SET status = 'Completed' WHERE consultation_id = ?", (proposal['consultation_id'],))

    # CRITICAL: Automatically initiate Custom Project Engagement in bookings table!
    start_dt = date.today().isoformat()
    delivery_dt = (date.today() + timedelta(days=proposal['delivery_days'])).isoformat()

    cursor.execute("""
        INSERT INTO bookings 
        (client_id, freelancer_id, service_id, proposal_id, booking_type, agreed_amount, start_date, delivery_date, requirements, status)
        VALUES (?, ?, NULL, ?, 'Custom', ?, ?, ?, ?, 'In Progress')
    """, (
        proposal['client_id'], 
        proposal['freelancer_id'], 
        proposal_id, 
        proposal['proposed_amount'], 
        start_dt, 
        delivery_dt, 
        f"Custom Project: {proposal['request_title']}\nScope: {proposal['scope']}"
    ))
    booking_id = cursor.lastrowid
    db.commit()
    db.close()

    flash(f"Congratulations! Proposal Version {proposal['version']} accepted. Custom engagement # {booking_id} is now active!", "success")
    return redirect(url_for('view_booking', booking_id=booking_id))


@app.route('/proposal/<int:proposal_id>/reject', methods=['POST'])
@login_required
def reject_proposal(proposal_id):
    db = get_db()
    proposal = db.execute("""
        SELECT p.*, c.client_id, c.freelancer_id 
        FROM proposals p
        JOIN consultations c ON p.consultation_id = c.consultation_id
        WHERE p.proposal_id = ?
    """, (proposal_id,)).fetchone()

    if not proposal:
        db.close()
        flash("Proposal not found.", "warning")
        return redirect(url_for('dashboard'))

    cursor = db.cursor()
    cursor.execute("UPDATE proposals SET status = 'Rejected' WHERE proposal_id = ?", (proposal_id,))
    db.commit()
    db.close()

    flash("Proposal declined.", "info")
    return redirect(url_for('negotiation_room', consultation_id=proposal['consultation_id']))

# -------------------------------------------------------------
# Model B: Fixed-Price Service Booking (Module 6 & 7)
# -------------------------------------------------------------

@app.route('/booking/service/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book_service(service_id):
    if session.get('role') != 'client':
        flash("Only clients can book fixed-price services.", "warning")
        return redirect(url_for('service_details', service_id=service_id))

    db = get_db()
    service = db.execute("""
        SELECT s.*, u.full_name as freelancer_name 
        FROM services s
        JOIN users u ON s.freelancer_id = u.user_id
        WHERE s.service_id = ? AND s.status = 'Active'
    """, (service_id,)).fetchone()

    if not service:
        db.close()
        flash("Service not found.", "warning")
        return redirect(url_for('browse_services'))

    if session.get('user_id') == service['freelancer_id']:
        db.close()
        flash("You cannot book your own service listing.", "danger")
        return redirect(url_for('service_details', service_id=service_id))

    if request.method == 'POST':
        start_date = request.form.get('start_date', '').strip()
        requirements = request.form.get('requirements', '').strip()

        if not start_date or not requirements:
            flash("Please specify a preferred start date and project requirements.", "danger")
            db.close()
            return render_template('booking.html', service=service, booking=None, review=None)

        # Calculate target delivery date
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_dt = date.today()
        delivery_dt = (start_dt + timedelta(days=service['delivery_days'])).isoformat()

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO bookings 
            (client_id, freelancer_id, service_id, proposal_id, booking_type, agreed_amount, start_date, delivery_date, requirements, status)
            VALUES (?, ?, ?, NULL, 'Fixed', ?, ?, ?, ?, 'Pending')
        """, (session['user_id'], service['freelancer_id'], service_id, service['price'], start_date, delivery_dt, requirements))
        booking_id = cursor.lastrowid
        db.commit()
        db.close()

        flash("Fixed-price service booking submitted! Awaiting freelancer confirmation.", "success")
        return redirect(url_for('view_booking', booking_id=booking_id))

    db.close()
    return render_template('booking.html', service=service, booking=None, review=None)


@app.route('/booking/<int:booking_id>')
@login_required
def view_booking(booking_id):
    db = get_db()
    booking = db.execute("""
        SELECT b.*, 
               uc.full_name as client_name, uc.email as client_email,
               uf.full_name as freelancer_name, uf.email as freelancer_email,
               s.title as service_title,
               c.request_title
        FROM bookings b
        JOIN users uc ON b.client_id = uc.user_id
        JOIN users uf ON b.freelancer_id = uf.user_id
        LEFT JOIN services s ON b.service_id = s.service_id
        LEFT JOIN proposals p ON b.proposal_id = p.proposal_id
        LEFT JOIN consultations c ON p.consultation_id = c.consultation_id
        WHERE b.booking_id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        db.close()
        flash("Order not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    curr_role = session.get('role')
    if curr_id not in [booking['client_id'], booking['freelancer_id']] and curr_role != 'admin':
        db.close()
        flash("Unauthorized access to this order.", "danger")
        return redirect(url_for('dashboard'))

    # Check for review
    review = db.execute("""
        SELECT r.*, u.full_name as client_name
        FROM reviews r
        JOIN users u ON r.client_id = u.user_id
        WHERE r.booking_id = ?
    """, (booking_id,)).fetchone()

    db.close()
    return render_template('booking.html', booking=booking, service=None, review=review)


@app.route('/booking/<int:booking_id>/status', methods=['POST'])
@login_required
def update_booking_status(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()

    if not booking:
        db.close()
        flash("Order not found.", "warning")
        return redirect(url_for('dashboard'))

    curr_id = session.get('user_id')
    if curr_id != booking['freelancer_id']:
        db.close()
        flash("Only the assigned freelancer can update order execution status.", "danger")
        return redirect(url_for('view_booking', booking_id=booking_id))

    new_status = request.form.get('status')
    deliverable_notes = request.form.get('deliverable_notes', '').strip()
    deliverable_file = request.files.get('deliverable_file')

    file_url = booking['deliverable_file']
    if deliverable_file and deliverable_file.filename:
        file_url = save_uploaded_file(deliverable_file, 'deliverables')

    if new_status in ['Accepted', 'In Progress', 'Delivered', 'Rejected', 'Cancelled']:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE bookings 
            SET status = ?, deliverable_notes = COALESCE(NULLIF(?, ''), deliverable_notes), deliverable_file = ?
            WHERE booking_id = ?
        """, (new_status, deliverable_notes, file_url, booking_id))
        db.commit()
        flash(f"Order status updated to: {new_status}", "success")

    db.close()
    return redirect(url_for('view_booking', booking_id=booking_id))


@app.route('/booking/<int:booking_id>/complete', methods=['POST'])
@login_required
def complete_booking(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()

    if not booking:
        db.close()
        flash("Order not found.", "warning")
        return redirect(url_for('dashboard'))

    if session.get('user_id') != booking['client_id']:
        db.close()
        flash("Only the hiring client can confirm project completion.", "danger")
        return redirect(url_for('view_booking', booking_id=booking_id))

    cursor = db.cursor()
    cursor.execute("UPDATE bookings SET status = 'Completed' WHERE booking_id = ?", (booking_id,))
    db.commit()
    db.close()

    flash("Project completion confirmed! You can now rate and review this freelancer below.", "success")
    return redirect(url_for('view_booking', booking_id=booking_id))

# -------------------------------------------------------------
# Module 8: Reviews & Feedback
# -------------------------------------------------------------

@app.route('/booking/<int:booking_id>/review', methods=['POST'])
@login_required
def submit_review(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()

    if not booking:
        db.close()
        flash("Booking not found.", "warning")
        return redirect(url_for('dashboard'))

    if session.get('user_id') != booking['client_id']:
        db.close()
        flash("Only the client can leave a review.", "danger")
        return redirect(url_for('view_booking', booking_id=booking_id))

    if booking['status'] != 'Completed':
        db.close()
        flash("Reviews are only permitted for completed engagements.", "warning")
        return redirect(url_for('view_booking', booking_id=booking_id))

    # Check if already reviewed
    existing = db.execute("SELECT review_id FROM reviews WHERE booking_id = ?", (booking_id,)).fetchone()
    if existing:
        db.close()
        flash("You have already reviewed this completed booking.", "info")
        return redirect(url_for('view_booking', booking_id=booking_id))

    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment', '').strip()

    if rating < 1 or rating > 5 or not comment:
        db.close()
        flash("Please provide a valid rating (1-5) and feedback comment.", "danger")
        return redirect(url_for('view_booking', booking_id=booking_id))

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO reviews (booking_id, client_id, freelancer_id, rating, comment)
        VALUES (?, ?, ?, ?, ?)
    """, (booking_id, booking['client_id'], booking['freelancer_id'], rating, comment))

    # Recalculate freelancer average rating
    cursor.execute("""
        SELECT AVG(rating), COUNT(review_id) FROM reviews WHERE freelancer_id = ?
    """, (booking['freelancer_id'],))
    avg_score, total_reviews = cursor.fetchone()

    cursor.execute("""
        UPDATE freelancer_profiles 
        SET rating_avg = ?, rating_count = ?
        WHERE user_id = ?
    """, (round(avg_score, 1), total_reviews, booking['freelancer_id']))

    db.commit()
    db.close()

    flash("Thank you! Your verified review and rating have been posted.", "success")
    return redirect(url_for('view_booking', booking_id=booking_id))

# -------------------------------------------------------------
# Module C: Client Requirement Board (Open Project Requests)
# -------------------------------------------------------------

@app.route('/client-requests')
def client_requests_board():
    query = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()

    sql = """
        SELECT cr.*, u.full_name as client_name,
               (SELECT COUNT(*) FROM client_request_interests WHERE request_id = cr.request_id) as interest_count
        FROM client_requests cr
        JOIN users u ON cr.client_id = u.user_id
        WHERE cr.status = 'Open'
    """
    params = []

    if query:
        sql += " AND (cr.title LIKE ? OR cr.description LIKE ? OR cr.required_skills LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term])

    if selected_category:
        sql += " AND cr.category = ?"
        params.append(selected_category)

    sql += " ORDER BY cr.created_at DESC"

    db = get_db()
    requests_list = db.execute(sql, params).fetchall()

    # If logged in as freelancer, mark which requests they've already expressed interest in
    user_id = session.get('user_id')
    role = session.get('role')
    decorated_requests = []
    for r in requests_list:
        r_dict = dict(r)
        if user_id and role == 'freelancer':
            interest = db.execute("""
                SELECT interest_id FROM client_request_interests 
                WHERE request_id = ? AND freelancer_id = ?
            """, (r['request_id'], user_id)).fetchone()
            r_dict['already_expressed'] = bool(interest)
        else:
            r_dict['already_expressed'] = False
        decorated_requests.append(r_dict)

    db.close()
    return render_template('client_requests.html', client_requests=decorated_requests, query=query, selected_category=selected_category)


@app.route('/client-requests/new', methods=['POST'])
@login_required
@role_required(['client'])
def create_client_request():
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Development')
    budget_min = float(request.form.get('budget_min', 0))
    budget_max = float(request.form.get('budget_max', 0))
    deadline = request.form.get('deadline', '').strip()
    required_skills = request.form.get('required_skills', '').strip()
    description = request.form.get('description', '').strip()

    if not title or not description or budget_min <= 0 or budget_max < budget_min:
        flash("Please provide a valid project title, budget range, and description.", "danger")
        return redirect(url_for('client_requests_board'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO client_requests 
        (client_id, title, description, category, required_skills, budget_min, budget_max, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open')
    """, (session['user_id'], title, description, category, required_skills, budget_min, budget_max, deadline))
    db.commit()
    db.close()

    flash("Your project requirement has been published! Freelancers can now review and express interest.", "success")
    return redirect(url_for('client_requests_board'))


@app.route('/client-requests/<int:request_id>')
@login_required
def client_request_details(request_id):
    db = get_db()
    client_request = db.execute("""
        SELECT cr.*, u.full_name as client_name
        FROM client_requests cr
        JOIN users u ON cr.client_id = u.user_id
        WHERE cr.request_id = ?
    """, (request_id,)).fetchone()

    if not client_request:
        db.close()
        flash("Requirement not found.", "warning")
        return redirect(url_for('client_requests_board'))

    # Check authorization (only the posting client or admin)
    if session.get('user_id') != client_request['client_id'] and session.get('role') != 'admin':
        db.close()
        flash("Unauthorized access.", "danger")
        return redirect(url_for('client_requests_board'))

    interests = db.execute("""
        SELECT cri.*, u.full_name as freelancer_name, u.avatar_url, p.headline, p.hourly_rate, p.rating_avg
        FROM client_request_interests cri
        JOIN users u ON cri.freelancer_id = u.user_id
        JOIN freelancer_profiles p ON u.user_id = p.user_id
        WHERE cri.request_id = ?
        ORDER BY cri.created_at DESC
    """, (request_id,)).fetchall()

    db.close()
    return render_template('client_request_details.html', client_request=client_request, interests=interests)


@app.route('/client-requests/<int:request_id>/interest', methods=['POST'])
@login_required
@role_required(['freelancer'])
def express_interest(request_id):
    message = request.form.get('message', '').strip()
    if not message:
        flash("Please provide a short pitch or intro note.", "warning")
        return redirect(url_for('client_requests_board'))

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO client_request_interests (request_id, freelancer_id, message, status)
            VALUES (?, ?, ?, 'Interested')
        """, (request_id, session['user_id'], message))
        db.commit()
        flash("Your expression of interest has been sent to the client!", "success")
    except Exception as e:
        flash("You have already expressed interest in this requirement.", "info")
    finally:
        db.close()

    return redirect(url_for('client_requests_board'))


@app.route('/client-requests/<int:request_id>/toggle', methods=['POST'])
@login_required
def toggle_client_request_status(request_id):
    db = get_db()
    client_request = db.execute("SELECT * FROM client_requests WHERE request_id = ?", (request_id,)).fetchone()

    if not client_request:
        db.close()
        flash("Requirement not found.", "warning")
        return redirect(url_for('client_requests_board'))

    if session.get('user_id') != client_request['client_id'] and session.get('role') != 'admin':
        db.close()
        flash("Unauthorized action.", "danger")
        return redirect(url_for('client_requests_board'))

    new_status = request.form.get('status', 'Closed')
    cursor = db.cursor()
    cursor.execute("UPDATE client_requests SET status = ? WHERE request_id = ?", (new_status, request_id))
    db.commit()
    db.close()

    flash(f"Requirement marked as {new_status}.", "info")
    return redirect(url_for('client_request_details', request_id=request_id))

# -------------------------------------------------------------
# Module 7: User Dashboards & Profile Editing
# -------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    role = session['role']
    db = get_db()

    user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if role == 'client':
        # Client view
        bookings = db.execute("""
            SELECT b.*, uf.full_name as freelancer_name, s.title as service_title, c.request_title
            FROM bookings b
            JOIN users uf ON b.freelancer_id = uf.user_id
            LEFT JOIN services s ON b.service_id = s.service_id
            LEFT JOIN proposals p ON b.proposal_id = p.proposal_id
            LEFT JOIN consultations c ON p.consultation_id = c.consultation_id
            WHERE b.client_id = ?
            ORDER BY b.created_at DESC
        """, (user_id,)).fetchall()

        consultations = db.execute("""
            SELECT c.*, uf.full_name as freelancer_name
            FROM consultations c
            JOIN users uf ON c.freelancer_id = uf.user_id
            WHERE c.client_id = ?
            ORDER BY c.created_at DESC
        """, (user_id,)).fetchall()

        my_requests = db.execute("""
            SELECT cr.*, 
                   (SELECT COUNT(*) FROM client_request_interests WHERE request_id = cr.request_id) as interest_count
            FROM client_requests cr
            WHERE cr.client_id = ?
            ORDER BY cr.created_at DESC
        """, (user_id,)).fetchall()

        reviews = db.execute("""
            SELECT r.*, u.full_name as client_name, s.title as service_title
            FROM reviews r
            JOIN users u ON r.client_id = u.user_id
            LEFT JOIN bookings b ON r.booking_id = b.booking_id
            LEFT JOIN services s ON b.service_id = s.service_id
            WHERE r.client_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,)).fetchall()

        active_bookings_count = sum(1 for b in bookings if b['status'] in ['Pending', 'Accepted', 'In Progress', 'Delivered'])
        completed_bookings_count = sum(1 for b in bookings if b['status'] == 'Completed')
        negotiations_count = sum(1 for c in consultations if c['status'] in ['Accepted', 'Reschedule Requested'])

        db.close()
        return render_template(
            'dashboard.html', 
            user=user, 
            bookings=bookings, 
            consultations=consultations, 
            my_requests=my_requests, 
            reviews=reviews,
            services=[],
            active_bookings_count=active_bookings_count,
            completed_bookings_count=completed_bookings_count,
            negotiations_count=negotiations_count,
            total_earnings=0
        )

    else:
        # Freelancer view
        bookings = db.execute("""
            SELECT b.*, uc.full_name as client_name, s.title as service_title, c.request_title
            FROM bookings b
            JOIN users uc ON b.client_id = uc.user_id
            LEFT JOIN services s ON b.service_id = s.service_id
            LEFT JOIN proposals p ON b.proposal_id = p.proposal_id
            LEFT JOIN consultations c ON p.consultation_id = c.consultation_id
            WHERE b.freelancer_id = ?
            ORDER BY b.created_at DESC
        """, (user_id,)).fetchall()

        consultations = db.execute("""
            SELECT c.*, uc.full_name as client_name
            FROM consultations c
            JOIN users uc ON c.client_id = uc.user_id
            WHERE c.freelancer_id = ?
            ORDER BY c.created_at DESC
        """, (user_id,)).fetchall()

        services = db.execute("""
            SELECT * FROM services WHERE freelancer_id = ? ORDER BY service_id DESC
        """, (user_id,)).fetchall()

        reviews = db.execute("""
            SELECT r.*, u.full_name as client_name, s.title as service_title
            FROM reviews r
            JOIN users u ON r.client_id = u.user_id
            LEFT JOIN bookings b ON r.booking_id = b.booking_id
            LEFT JOIN services s ON b.service_id = s.service_id
            WHERE r.freelancer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,)).fetchall()

        active_bookings_count = sum(1 for b in bookings if b['status'] in ['Pending', 'Accepted', 'In Progress', 'Delivered'])
        completed_bookings_count = sum(1 for b in bookings if b['status'] == 'Completed')
        total_earnings = sum(b['agreed_amount'] for b in bookings if b['status'] in ['In Progress', 'Delivered', 'Completed'])
        negotiations_count = sum(1 for c in consultations if c['status'] in ['Accepted', 'Pending'])

        db.close()
        return render_template(
            'dashboard.html', 
            user=user, 
            bookings=bookings, 
            consultations=consultations, 
            services=services, 
            reviews=reviews,
            my_requests=[],
            active_bookings_count=active_bookings_count,
            completed_bookings_count=completed_bookings_count,
            negotiations_count=negotiations_count,
            total_earnings=total_earnings
        )


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_id = session['user_id']
    role = session['role']
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    profile = db.execute("SELECT * FROM freelancer_profiles WHERE user_id = ?", (user_id,)).fetchone() if role == 'freelancer' else None

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        avatar_file = request.files.get('avatar_file')
        avatar_url = user['avatar_url']

        if avatar_file and avatar_file.filename:
            saved_path = save_uploaded_file(avatar_file, 'profiles')
            if saved_path:
                avatar_url = saved_path

        cursor = db.cursor()
        cursor.execute("UPDATE users SET full_name = ?, avatar_url = ? WHERE user_id = ?", (full_name, avatar_url, user_id))
        session['full_name'] = full_name
        session['avatar_url'] = avatar_url

        if role == 'freelancer':
            headline = request.form.get('headline', '').strip()
            category = request.form.get('category', 'Development')
            experience = int(request.form.get('experience', 0))
            hourly_rate = float(request.form.get('hourly_rate', 500))
            availability = request.form.get('availability', 'Available')
            skills = request.form.get('skills', '').strip()
            portfolio_url = request.form.get('portfolio_url', '').strip()
            bio = request.form.get('bio', '').strip()

            cursor.execute("""
                UPDATE freelancer_profiles 
                SET headline = ?, category = ?, experience = ?, hourly_rate = ?, availability = ?, skills = ?, portfolio_url = ?, bio = ?
                WHERE user_id = ?
            """, (headline, category, experience, hourly_rate, availability, skills, portfolio_url, bio, user_id))

        db.commit()
        db.close()

        flash("Profile updated successfully!", "success")
        return redirect(url_for('dashboard'))

    db.close()
    return render_template('profile_edit.html', user=user, profile=profile)


@app.route('/service/create', methods=['POST'])
@login_required
@role_required(['freelancer'])
def create_service():
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Development')
    price = float(request.form.get('price', 0))
    delivery_days = int(request.form.get('delivery_days', 1))
    revisions = int(request.form.get('revisions', 1))
    deliverables = request.form.get('deliverables', '').strip()
    description = request.form.get('description', '').strip()
    image_file = request.files.get('image_file')

    image_url = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600"
    if image_file and image_file.filename:
        saved_img = save_uploaded_file(image_file, 'services')
        if saved_img:
            image_url = saved_img

    if not title or not description or price <= 0:
        flash("Please provide a valid title, description, and price.", "danger")
        return redirect(url_for('dashboard'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO services 
        (freelancer_id, title, description, category, price, delivery_days, deliverables, revisions, status, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
    """, (session['user_id'], title, description, category, price, delivery_days, deliverables, revisions, image_url))
    db.commit()
    db.close()

    flash("New fixed-price service package published successfully!", "success")
    return redirect(url_for('dashboard'))


@app.route('/service/<int:service_id>/delete', methods=['POST'])
@login_required
@role_required(['freelancer'])
def delete_service(service_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM services WHERE service_id = ? AND freelancer_id = ?", (service_id, session['user_id']))
    db.commit()
    db.close()

    flash("Service package removed.", "info")
    return redirect(url_for('dashboard'))

# -------------------------------------------------------------
# Module 9: Admin Dashboard & Platform Moderation
# -------------------------------------------------------------

@app.route('/admin')
@login_required
@role_required(['admin'])
def admin_dashboard():
    db = get_db()

    # KPI Statistics
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_freelancers = db.execute("SELECT COUNT(*) FROM users WHERE role = 'freelancer'").fetchone()[0]
    total_clients = db.execute("SELECT COUNT(*) FROM users WHERE role = 'client'").fetchone()[0]
    total_services = db.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    total_consultations = db.execute("SELECT COUNT(*) FROM consultations").fetchone()[0]
    total_bookings = db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    total_gmv = db.execute("SELECT COALESCE(SUM(agreed_amount), 0) FROM bookings WHERE status IN ('In Progress', 'Delivered', 'Completed')").fetchone()[0]

    stats = {
        'total_users': total_users,
        'total_freelancers': total_freelancers,
        'total_clients': total_clients,
        'total_services': total_services,
        'total_consultations': total_consultations,
        'total_bookings': total_bookings,
        'total_gmv': total_gmv
    }

    users = db.execute("SELECT * FROM users ORDER BY user_id DESC").fetchall()

    services = db.execute("""
        SELECT s.*, u.full_name as freelancer_name 
        FROM services s
        JOIN users u ON s.freelancer_id = u.user_id
        ORDER BY s.service_id DESC
    """).fetchall()

    bookings = db.execute("""
        SELECT b.*, uc.full_name as client_name, uf.full_name as freelancer_name, s.title as service_title, c.request_title
        FROM bookings b
        JOIN users uc ON b.client_id = uc.user_id
        JOIN users uf ON b.freelancer_id = uf.user_id
        LEFT JOIN services s ON b.service_id = s.service_id
        LEFT JOIN proposals p ON b.proposal_id = p.proposal_id
        LEFT JOIN consultations c ON p.consultation_id = c.consultation_id
        ORDER BY b.booking_id DESC
    """).fetchall()

    db.close()
    return render_template('admin.html', stats=stats, users=users, services=services, bookings=bookings)


@app.route('/admin/user/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_toggle_user(user_id):
    new_status = request.form.get('status', 'active')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE user_id = ? AND role != 'admin'", (new_status, user_id))
    db.commit()
    db.close()

    flash(f"User account status updated to: {new_status}", "info")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/service/<int:service_id>/toggle', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_toggle_service(service_id):
    new_status = request.form.get('status', 'Active')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE services SET status = ? WHERE service_id = ?", (new_status, service_id))
    db.commit()
    db.close()

    flash(f"Service status updated to: {new_status}", "info")
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
