-- FreelanceConnect Database Schema
PRAGMA foreign_keys = ON;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('client', 'freelancer', 'admin')),
    avatar_url TEXT DEFAULT '',
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'suspended')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Freelancer Profiles Table
CREATE TABLE IF NOT EXISTS freelancer_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    headline TEXT DEFAULT '',
    skills TEXT DEFAULT '',
    category TEXT DEFAULT 'Development',
    experience INTEGER DEFAULT 0,
    bio TEXT DEFAULT '',
    portfolio_url TEXT DEFAULT '',
    hourly_rate REAL DEFAULT 0.0,
    availability TEXT DEFAULT 'Available' CHECK(availability IN ('Available', 'Busy')),
    rating_avg REAL DEFAULT 5.0,
    rating_count INTEGER DEFAULT 0
);

-- 3. Services Table (Fixed-Price Packages)
CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    freelancer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    delivery_days INTEGER NOT NULL,
    deliverables TEXT NOT NULL,
    revisions INTEGER DEFAULT 1,
    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
    image_url TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Consultations Table (Meeting & Project Requests)
CREATE TABLE IF NOT EXISTS consultations (
    consultation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    freelancer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    request_title TEXT NOT NULL,
    project_description TEXT NOT NULL,
    preferred_datetime TEXT NOT NULL,
    meeting_type TEXT DEFAULT 'Online' CHECK(meeting_type IN ('Online', 'In-person')),
    meeting_link TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    rescheduled_datetime TEXT DEFAULT '',
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Accepted', 'Rejected', 'Reschedule Requested', 'Completed', 'Cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. Client Requests Table (Open Project Requirements Board)
CREATE TABLE IF NOT EXISTS client_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    required_skills TEXT DEFAULT '',
    budget_min REAL DEFAULT 0.0,
    budget_max REAL DEFAULT 0.0,
    deadline TEXT DEFAULT '',
    status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'Closed')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. Client Request Interests Table (Freelancers expressing interest)
CREATE TABLE IF NOT EXISTS client_request_interests (
    interest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES client_requests(request_id) ON DELETE CASCADE,
    freelancer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message TEXT DEFAULT '',
    status TEXT DEFAULT 'Interested' CHECK(status IN ('Interested', 'Invited', 'Declined')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(request_id, freelancer_id)
);

-- 7. Proposals Table (Initial Offers & Counter-offers for Consultations)
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    consultation_id INTEGER NOT NULL REFERENCES consultations(consultation_id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    proposed_amount REAL NOT NULL,
    delivery_days INTEGER NOT NULL,
    scope TEXT NOT NULL,
    message TEXT DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Accepted', 'Rejected', 'Superseded')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 8. Bookings Table (Handles Fixed-price and Custom engagements)
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    freelancer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(service_id) ON DELETE SET NULL,
    proposal_id INTEGER REFERENCES proposals(proposal_id) ON DELETE SET NULL,
    booking_type TEXT NOT NULL CHECK(booking_type IN ('Fixed', 'Custom')),
    agreed_amount REAL NOT NULL,
    start_date TEXT NOT NULL,
    delivery_date TEXT NOT NULL,
    requirements TEXT NOT NULL,
    deliverable_notes TEXT DEFAULT '',
    deliverable_file TEXT DEFAULT '',
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Accepted', 'In Progress', 'Delivered', 'Completed', 'Rejected', 'Cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Reviews Table (Ratings & Feedback for completed bookings)
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    client_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    freelancer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_services_category ON services(category);
CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);
CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_proposals_consultation ON proposals(consultation_id);
