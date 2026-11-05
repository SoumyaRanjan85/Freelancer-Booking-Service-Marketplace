# FreelanceConnect – Dual-Model Freelancer Marketplace Platform

[![Python 3.13](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![Flask 3.1.3](https://img.shields.io/badge/Flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)](https://www.sqlite.org/)
[![Bootstrap 5](https://img.shields.io/badge/UI-Bootstrap%205-purple.svg)](https://getbootstrap.com/)

A modern, choice-driven freelance marketplace that connects clients with verified professionals through **two distinct hiring models** (alongside an open client requirement board), eliminating the race-to-the-bottom bidding wars found in conventional freelance platforms.

---

## 🌟 The Core Differentiating Concept: Flexible Hiring Architecture

### 1. Model A — Consultation-Based Project Hiring (Custom Work)
**Discuss &rarr; Negotiate &rarr; Agree &rarr; Hire**
* **Best for**: E-commerce stores, custom software, full-stack apps, or projects with evolving requirements.
* **Workflow**:
  1. Client discovers a freelancer and requests a consultation meeting (Online or In-person).
  2. Freelancer accepts the meeting and shares an external meeting link (e.g. Google Meet or Zoom).
  3. Following discussions, the freelancer submits a structured **Formal Proposal** (Version 1).
  4. The client can either **Accept** or submit a **Counterproposal** (Version 2).
  5. The freelancer can accept the counterproposal or iterate further. Full negotiation audit trail is preserved.
  6. Upon mutual agreement, the system automatically converts the proposal into an active **Custom Project Engagement**.

### 2. Model B — Fixed-Price Service Booking (Instant Packages)
**Select &rarr; Book &rarr; Confirm &rarr; Deliver**
* **Best for**: Logo designs, landing pages, SEO blog posts, bug fixes, and well-defined tasks.
* **Workflow**:
  1. Freelancers publish predefined service packages with fixed prices, delivery days, and deliverables.
  2. Client discovers the package and books it directly with project instructions and preferred start date.
  3. Freelancer accepts the order and moves it to *In Progress*.
  4. Freelancer submits final deliverables.
  5. Client confirms completion and unlocks the verified 5-star review system.

### 3. Model C — Client Project Requirements Board (Open Briefs)
**Post Brief &rarr; Review Pitches &rarr; Invite &rarr; Consult**
* Clients post open project briefs with budget ranges and target deadlines.
* Freelancers browse and **Express Interest** with custom pitches (no downward price bidding).
* Clients review interested candidate pitches and invite their top choice directly into a consultation.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- No Node.js or npm build steps required (uses modern Bootstrap 5 and Font Awesome 6 CDNs).

### 2. Installation & Running
In your terminal, navigate to the project directory:
```powershell
# 1. Install dependencies (Flask & Werkzeug)
pip install -r requirements.txt

# 2. Seed database with realistic demo data (users, services, consultations, bookings, reviews)
python database.py

# 3. Launch Flask server
python app.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

### 3. Run Automated Tests
Execute the 10-point test suite covering authentication, RBAC, Model A, Model B, and Model C:
```powershell
python -m unittest test_app.py -v
```

---

## 🔑 Pre-Seeded Demo Accounts

The `/login` page includes **1-Click AutoFill** buttons for primary evaluation accounts for quick role-switching.

| Role | Name | Email | Password | 1-Click AutoFill | Details |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Admin** | Marketplace Admin | `admin@freelanceconnect.com` | `admin123` | ✅ | Platform KPIs, user moderation, service moderation |
| **Client 1** | Arjun Mehta | `client@example.com` | `client123` | ✅ | Active custom e-commerce project, posted requirements |
| **Client 2** | Priya Sharma | `priya@example.com` | `client123` | ❌ | Completed fixed-price logo booking with review |
| **Freelancer 1** | Vikram Rao | `freelancer@example.com` | `freelancer123` | ✅ | Full-Stack Python & Flask Developer |
| **Freelancer 2** | Ananya Sen | `designer@example.com` | `designer123` | ✅ | UI/UX & Brand Identity Designer |
| **Freelancer 3** | Rohan Verma | `writer@example.com` | `writer123` | ❌ | Technical Copywriter & SEO Specialist |
| **Freelancer 4** | Neha Patel | `mobile@example.com` | `mobile123` | ❌ | Flutter & Mobile App Developer |

*Note: Additional domain experts (AI, DevOps, Web3, 3D, Cybersecurity, Analytics) are also pre-seeded with password `password123`.*

---

## 🎬 How to Demonstrate During Evaluation

### Scenario 1: Custom Project Hiring (Model A)
1. Log in as **Client** using the 1-click button (`client@example.com` / `client123`).
2. Go to **Explore Freelancers** &rarr; select **Neha Patel** (Flutter Developer).
3. Click **Consult** &rarr; submit project title: *"Mobile Food Delivery App"*, meeting slot, and requirements.
4. Log out and log in as **Freelancer** (`mobile@example.com` / `mobile123`).
5. In **Dashboard &rarr; Consultations**, accept the meeting and provide a Google Meet link.
6. Open **Negotiation Workspace** &rarr; submit an initial proposal: **₹15,000**, 10 days, scope details.
7. Log back in as **Client** (`client@example.com` / `client123`).
8. In **Dashboard &rarr; Consultations &rarr; Negotiation Workspace**, click **Make Counterproposal**: **₹13,500**, 8 days.
9. Log in as **Freelancer** &rarr; accept the Counterproposal.
10. Notice how the proposal status becomes **Accepted** and a **Custom Project Engagement** is automatically spawned in both user dashboards!

### Scenario 2: Fixed-Price Service Booking & Review (Model B)
1. Log in as **Client** (`client@example.com` / `client123`).
2. Go to **Fixed Services** &rarr; pick *"Complete Brand Identity & Modern Vector Logo Suite"* (₹1,499).
3. Click **Book Now** &rarr; enter start date and brand instructions.
4. Log in as **Designer** using the 1-click button (`designer@example.com` / `designer123`).
5. In **Dashboard &rarr; Orders & Custom Projects**, accept the booking and mark it **In Progress**.
6. When work is done, submit final deliverable notes & files &rarr; status becomes **Delivered**.
7. Log in as **Client** &rarr; click **Confirm Project Completion**.
8. Fill out the **5-Star Rating & Review Form**.
9. Go to the Designer's public profile: the new review appears and the average rating is recalculated automatically!

### Scenario 3: Open Project Requirements Board (Model C)
1. Log in as **Client** (`client@example.com` / `client123`).
2. Go to **Client Requests** &rarr; click **Post New Requirement**.
3. Submit a project brief with category, required skills, budget range (e.g., ₹20,000 - ₹35,000), and deadline.
4. Log out and log in as **Freelancer** (`freelancer@example.com` / `freelancer123`).
5. Go to **Client Requests** &rarr; open the newly posted requirement &rarr; submit an **Expression of Interest** with a tailored pitch.
6. Log back in as **Client** &rarr; open the requirement to review interested candidate pitches &rarr; click **Invite to Consultation** to seamlessly transition to Model A.

---

## 🗄️ Database Architecture (SQLite3)

The database schema (`database/schema.sql`) contains 9 relational tables:
1. **`users`**: Client, Freelancer, and Admin accounts with hashed passwords and status (`active`, `suspended`).
2. **`freelancer_profiles`**: Professional headlines, skills (comma-separated), experience, bio, portfolio URL, hourly rate, availability, and rating aggregates.
3. **`services`**: Predefined fixed-price packages, delivery timelines, deliverables checklist, revisions count, status (`Active`, `Inactive`).
4. **`consultations`**: Model A meeting requests, date/times, meeting links, notes, and statuses (`Pending`, `Accepted`, `Rejected`, `Reschedule Requested`, `Completed`, `Cancelled`).
5. **`client_requests`**: Model C open requirement board briefs with budget min/max and target deadlines (`Open`, `Closed`).
6. **`client_request_interests`**: Freelancers expressing interest in client requirements (`Interested`, `Invited`, `Declined`).
7. **`proposals`**: Negotiation iterations storing version numbers, proposed amounts, delivery days, scope, and status (`Pending`, `Accepted`, `Rejected`, `Superseded`).
8. **`bookings`**: Unified tracking table handling both Fixed services (`service_id`) and Custom engagements (`proposal_id`) across 5 lifecycle stages (`Pending` &rarr; `Accepted` &rarr; `In Progress` &rarr; `Delivered` &rarr; `Completed`), plus terminal states (`Rejected`, `Cancelled`).
9. **`reviews`**: Verified 1–5 star ratings and feedback linked uniquely to completed bookings.

---

## 📁 Project Structure

```text
Freelance Portal/
├── app.py                     # Central Flask backend, routes & business logic
├── config.py                  # App configuration & file upload parameters
├── database.py                # Database connection, initialization & seed script
├── requirements.txt           # Python dependencies (Flask, Werkzeug)
├── test_app.py                # Automated end-to-end unittest suite
├── database/
│   ├── schema.sql             # Relational DDL schema & table constraints
│   └── freelanceconnect.db    # SQLite database file
├── static/
│   ├── css/
│   │   └── style.css          # Modern marketplace custom stylesheet
│   ├── js/
│   │   └── main.js            # Toast notifications, autofill & helpers
│   └── uploads/               # Uploaded avatars, service covers, and deliverables
├── templates/
│   ├── base.html              # Master layout with responsive navbar & footer
│   ├── index.html             # Homepage highlighting Two Ways to Hire
│   ├── explore.html           # Multi-filter freelancer search
│   ├── freelancer_profile.html# Full profile with skills, services & reviews
│   ├── services.html          # Fixed-price service marketplace catalog
│   ├── service_details.html   # Service package breakdown
│   ├── consultation.html      # Consultation meeting request & management
│   ├── negotiation.html       # Proposal & counteroffer negotiation workspace
│   ├── booking.html           # Booking checkout & unified order progress tracker
│   ├── client_requests.html   # Open requirement board (Model C)
│   ├── client_request_details.html # Candidate pitch review & invite
│   ├── dashboard.html         # Role-aware dashboard for Clients & Freelancers
│   ├── profile_edit.html      # User profile editor
│   ├── admin.html             # Governance & platform moderation dashboard
│   └── auth/
│       ├── login.html         # Login with 1-click quick demo buttons
│       └── register.html      # Registration with role selector
└── utils/
    ├── auth.py                # RBAC decorators & password hashing
    └── validation.py          # Input sanitization & safe file storage
```

---

## 🔮 Future Enhancements
* Integrated Razorpay / Stripe payment gateway and escrow handling.
* In-app WebRTC video conferencing for consultations.
* Real-time WebSocket messaging for project collaboration.
* AI-driven talent recommendation matching client requirements.
