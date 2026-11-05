import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import Config

# Comprehensive Taxonomy of 1,000+ Skills across 12 Industry Domains
SKILLS_TAXONOMY = {
    "AI & Data Science": [
        "Large Language Models (LLMs)", "Prompt Engineering", "PyTorch", "TensorFlow", "LangChain", 
        "Retrieval-Augmented Generation (RAG)", "OpenAI API", "HuggingFace", "Computer Vision", 
        "Natural Language Processing (NLP)", "Fine-Tuning", "Vector Databases (Pinecone/Milvus)", 
        "Deep Learning", "Data Mining", "Machine Learning Ops (MLOps)", "Keras", "Scikit-Learn", 
        "Data Engineering", "Pandas & NumPy", "Transformers", "Stable Diffusion", "Whisper AI",
        "Predictive Modeling", "Neural Networks", "Generative AI", "Statistical Modeling", "Autonomous Agents"
    ],
    "Web & Full-Stack Development": [
        "Python", "Flask", "Django", "FastAPI", "React.js", "Next.js", "Node.js", "Express.js", 
        "TypeScript", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Bootstrap 5", "Vue.js", "Nuxt.js", 
        "Angular", "PHP", "Laravel", "Ruby on Rails", "Go (Golang)", "Rust", "ASP.NET Core", 
        "GraphQL", "RESTful APIs", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Prisma ORM", 
        "WebSockets", "Microservices", "PWA Development", "Supabase", "Firebase", "WordPress Development"
    ],
    "Mobile App Development": [
        "Flutter", "Dart", "React Native", "Swift", "SwiftUI", "Kotlin", "Java (Android)", 
        "iOS App Development", "Android App Development", "Cross-Platform Mobile Apps", "Expo", 
        "Mobile UI/UX", "Mobile Payment Gateways", "Push Notifications (APNs/FCM)", "Offline Sync", 
        "SQLite Mobile", "Realm Database", "Bluetooth LE Integration", "Mobile Security", "App Store Optimization (ASO)"
    ],
    "UI/UX & Product Design": [
        "Figma", "UI/UX Design", "Wireframing", "Interactive Prototyping", "Design Systems", 
        "User Journey Mapping", "Information Architecture", "Usability Testing", "Mobile UI Design", 
        "Web App UI", "Micro-Interactions", "Framer", "Adobe XD", "Design Sprint", "Accessibility (WCAG)", 
        "Component Libraries", "Human-Centered Design", "User Persona Research", "Typography & Color Theory"
    ],
    "Brand Identity & Graphic Design": [
        "Logo Design", "Brand Identity Guidelines", "Vector Art", "Adobe Illustrator", "Adobe Photoshop", 
        "Packaging Design", "3D Brand Assets", "Pitch Deck Design", "Infographics", "Iconography", 
        "Merchandise & Apparel Design", "Print Design", "Banner Ad Design", "Stationery Design", "Custom Lettering"
    ],
    "Technical Writing & SEO": [
        "Technical Documentation", "API Reference Writing", "Developer Guides", "Whitepapers", 
        "Technical Blogging", "SEO Content Writing", "Software Architecture Docs", "Markdown", 
        "Swagger/OpenAPI Docs", "GitBook Documentation", "Case Studies", "Copywriting", "SaaS Landing Page Copy"
    ],
    "DevOps, Cloud & Infrastructure": [
        "Docker", "Kubernetes", "Amazon Web Services (AWS)", "Google Cloud Platform (GCP)", 
        "Microsoft Azure", "CI/CD Pipelines", "GitHub Actions", "Terraform (IaC)", "Linux System Administration", 
        "Nginx", "Apache", "Serverless Architecture", "Prometheus & Grafana", "Database Replication", "VPC Networking"
    ],
    "Digital Marketing & Growth": [
        "Search Engine Optimization (SEO)", "Technical SEO Auditing", "Google Ads (PPC)", "Meta Ads Management", 
        "Conversion Rate Optimization (CRO)", "Email Marketing Automation", "HubSpot", "Google Analytics 4", 
        "Growth Hacking", "Social Media Marketing", "Content Strategy", "Affiliate Marketing", "App Store Ads"
    ],
    "Blockchain & Web3": [
        "Solidity", "Smart Contract Auditing", "Ethereum", "Polygon", "Solana", "Web3.js", "Ethers.js", 
        "Hardhat", "Foundry", "NFT Minting Systems", "DeFi Protocols", "ERC-20 & ERC-721", "Decentralized Apps (DApps)"
    ],
    "Video & Motion Design": [
        "Blender 3D", "After Effects", "Adobe Premiere Pro", "Motion Graphics", "3D Product Animation", 
        "Logo Animation", "Explainer Videos", "Sound Design", "Color Grading (DaVinci Resolve)", "Video Editing"
    ],
    "Business, Finance & Analytics": [
        "Power BI", "Tableau", "SQL Business Analytics", "Financial Modeling", "Excel VBA & Macros", 
        "Pitch Deck Financials", "SaaS Metrics & KPIs", "Market Research", "Competitive Benchmarking", "Budget Forecasting"
    ],
    "Game Development & XR": [
        "Unity Engine", "Unreal Engine 5", "C# for Unity", "C++ for Unreal", "3D Game Environment", 
        "Gameplay Mechanics", "Shaders & Visual Effects", "AR/VR Development", "Physics Simulation", "Multiplayer Netcode"
    ]
}

def get_db():
    """Get a database connection with Row factory and foreign keys enabled."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables using schema.sql and apply incremental migrations."""
    conn = get_db()
    with open(Config.SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    
    # Auto-migration check: ensure escrow_status exists on bookings
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(bookings);")
    cols = [r['name'] for r in cursor.fetchall()]
    if 'escrow_status' not in cols:
        cursor.execute("ALTER TABLE bookings ADD COLUMN escrow_status TEXT DEFAULT 'Pending_Deposit';")
        cursor.execute("UPDATE bookings SET escrow_status = 'Released' WHERE status = 'Completed';")
        cursor.execute("UPDATE bookings SET escrow_status = 'Escrow_Locked' WHERE status IN ('Accepted', 'In Progress', 'Delivered');")
        conn.commit()

    conn.close()
    print("Database initialized successfully.")

def seed_db(force: bool = False):
    """Seed database with massive realistic demo accounts, services, consultations, proposals, bookings, and reviews."""
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Check if already seeded and not force
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count >= 10 and not force:
        # Check if transactions and wallets exist
        cursor.execute("SELECT COUNT(*) FROM user_wallets")
        wallet_count = cursor.fetchone()[0]
        if wallet_count < 10:
            print("Populating missing wallets and transactions...")
            _seed_wallets_and_transactions(conn)
        else:
            print("Database already contains extensive data. Skipping seed.")
        conn.close()
        return

    if force:
        print("Force re-seeding: clearing existing data...")
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("DELETE FROM user_wallets")
        cursor.execute("DELETE FROM project_milestones")
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM reviews")
        cursor.execute("DELETE FROM bookings")
        cursor.execute("DELETE FROM proposals")
        cursor.execute("DELETE FROM client_request_interests")
        cursor.execute("DELETE FROM client_requests")
        cursor.execute("DELETE FROM consultations")
        cursor.execute("DELETE FROM services")
        cursor.execute("DELETE FROM freelancer_profiles")
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM sqlite_sequence")
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.commit()

    print("Seeding database with expanded 14+ professionals, 14+ fixed services, and multi-category data...")

    # Passwords hashed with Werkzeug
    pw_default = generate_password_hash("password123")
    pw_admin = generate_password_hash("admin123")
    pw_client = generate_password_hash("client123")
    pw_freelancer = generate_password_hash("freelancer123")
    pw_designer = generate_password_hash("designer123")
    pw_writer = generate_password_hash("writer123")
    pw_mobile = generate_password_hash("mobile123")

    # 1. Insert Users (Admin, Clients, and 12 Elite Freelancers across categories)
    users_data = [
        # Admin & Clients
        (1, "Marketplace Admin", "admin@freelanceconnect.com", pw_admin, "admin", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"),
        (2, "Arjun Mehta", "client@example.com", pw_client, "client", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80"),
        (3, "Priya Sharma", "priya@example.com", pw_client, "client", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80"),
        (4, "David Chen", "david@example.com", pw_client, "client", "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80"),

        # 12 Diverse Freelancers
        (5, "Vikram Rao", "freelancer@example.com", pw_freelancer, "freelancer", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150&auto=format&fit=crop&q=80"),
        (6, "Ananya Sen", "designer@example.com", pw_designer, "freelancer", "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80"),
        (7, "Rohan Verma", "writer@example.com", pw_writer, "freelancer", "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80"),
        (8, "Neha Patel", "mobile@example.com", pw_mobile, "freelancer", "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80"),
        (9, "Dr. Aakash Kulkarni", "ai@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=150&auto=format&fit=crop&q=80"),
        (10, "Marcus Vance", "devops@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=150&auto=format&fit=crop&q=80"),
        (11, "Elena Rostova", "web3@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1534751516642-a1714f5a5e3e?w=150&auto=format&fit=crop&q=80"),
        (12, "Tariq Mansoor", "video@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?w=150&auto=format&fit=crop&q=80"),
        (13, "Sarah Jenkins", "cyber@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80"),
        (14, "Maya Lin", "analytics@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80"),
        (15, "Kenji Takahashi", "game@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150&auto=format&fit=crop&q=80"),
        (16, "Chloe Dubois", "growth@example.com", pw_default, "freelancer", "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=150&auto=format&fit=crop&q=80")
    ]

    cursor.executemany("""
        INSERT INTO users (user_id, full_name, email, password_hash, role, avatar_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, users_data)

    # 2. Insert Freelancer Profiles (12 distinct experts)
    freelancer_profiles = [
        # (user_id, headline, skills, category, experience, bio, portfolio_url, hourly_rate, availability, rating_avg, rating_count)
        (
            5, 
            "Principal Full-Stack Python & Flask Architect", 
            "Python, Flask, SQLite, React, PostgreSQL, REST APIs, Docker, GraphQL", 
            "Development", 
            8, 
            "High-performance backend engineer specializing in clean Python architectures, scalable database schemas, and robust API development. Built scalable web applications for dozens of global startups.", 
            "https://github.com/vikramrao-dev", 
            1600.0, "Available", 4.9, 28
        ),
        (
            6, 
            "Staff UI/UX Designer & Brand Strategist", 
            "Figma, UI/UX Design, Design Systems, Wireframing, Brand Identity, Logo Design", 
            "Design", 
            6, 
            "Obsessed with crafting intuitive, aesthetic product interfaces and memorable brands. Specializing in SaaS dashboards, conversion-optimized checkout flows, and design systems.", 
            "https://dribbble.com/ananyadesigns", 
            1350.0, "Available", 5.0, 36
        ),
        (
            7, 
            "Technical Content Strategist & Senior Tech Writer", 
            "Technical Documentation, SEO Writing, API Reference, Copywriting, Whitepapers", 
            "Writing", 
            5, 
            "Translating complex engineering concepts into lucid, high-ranking developer docs and persuasive SaaS copy. Former technical editor at top developer publications.", 
            "https://medium.com/@rohanverma", 
            950.0, "Available", 4.9, 19
        ),
        (
            8, 
            "Senior Cross-Platform Mobile Engineer (Flutter & iOS)", 
            "Flutter, Dart, Mobile UI, Swift, Firebase, SQLite Mobile, Push Notifications", 
            "Mobile Apps", 
            7, 
            "Crafting pixel-perfect, 60fps mobile applications with smooth offline synchronizations, payment integrations, and modular state management.", 
            "https://github.com/nehapatel-apps", 
            1900.0, "Available", 4.9, 23
        ),
        (
            9, 
            "AI Research Engineer & Generative LLM Specialist", 
            "Large Language Models (LLMs), RAG, Prompt Engineering, PyTorch, LangChain, Vector Databases", 
            "AI & Data Science", 
            9, 
            "PhD in Machine Learning. Designing enterprise RAG architectures, LLM fine-tuning pipelines, and intelligent agent workflows with measurable latency and cost optimization.", 
            "https://huggingface.co/akulkarni-ai", 
            2800.0, "Available", 5.0, 17
        ),
        (
            10, 
            "Lead Cloud Architect & DevOps Kubernetes Specialist", 
            "Docker, Kubernetes, AWS, Terraform (IaC), CI/CD Pipelines, Linux System Admin", 
            "DevOps & Cloud", 
            10, 
            "Certified AWS Solutions Architect. Automating zero-downtime deployment pipelines, resilient multi-cloud architectures, and Kubernetes cluster management.", 
            "https://github.com/marcusvance-devops", 
            2200.0, "Available", 4.8, 31
        ),
        (
            11, 
            "Smart Contract Security Auditor & Web3 Engineer", 
            "Solidity, Smart Contract Auditing, Ethereum, Web3.js, Hardhat, DeFi Protocols", 
            "Blockchain & Web3", 
            6, 
            "Securing decentralized finance protocols and writing gas-optimized smart contracts. Audited over 40+ EVM contracts with zero post-launch exploits.", 
            "https://github.com/elenarostova-security", 
            2500.0, "Available", 4.9, 14
        ),
        (
            12, 
            "3D Motion Designer & Blender Visual Effects Artist", 
            "Blender 3D, After Effects, 3D Product Animation, Motion Graphics, Video Editing", 
            "Video & Motion", 
            5, 
            "Creating photorealistic 3D product animations, cinematic brand reveal trailers, and snappy micro-animations for high-growth tech products.", 
            "https://behance.net/tariqmansoor3d", 
            1500.0, "Available", 4.9, 21
        ),
        (
            13, 
            "Cybersecurity Consultant & Ethical Penetration Tester", 
            "Cybersecurity, Penetration Testing, OWASP Top 10, Network Security, Vulnerability Auditing", 
            "Cybersecurity", 
            8, 
            "OSCP-certified ethical hacker protecting web applications and cloud APIs against vulnerabilities, data leaks, and unauthorized lateral escalation.", 
            "https://sarahjenkins-security.io", 
            2400.0, "Available", 5.0, 16
        ),
        (
            14, 
            "Senior BI Analyst & SaaS Financial Modeling Expert", 
            "Power BI, Tableau, SQL Analytics, Financial Modeling, Excel VBA & Macros", 
            "Business & Analytics", 
            6, 
            "Building automated interactive executive dashboards, cohort retention models, and investor-ready unit economic financial plans for tech companies.", 
            "https://mayalin-analytics.com", 
            1400.0, "Available", 4.8, 25
        ),
        (
            15, 
            "Lead Unity & Unreal Engine Game Developer", 
            "Unity Engine, Unreal Engine 5, C# for Unity, 3D Game Environment, Shaders & VFX", 
            "Game Development", 
            7, 
            "Game developer with two commercially published titles. Expert in multiplayer netcode, performant mobile game physics, and stylized 3D environments.", 
            "https://kenjigames.artstation.com", 
            1750.0, "Available", 4.9, 18
        ),
        (
            16, 
            "Senior Growth Hacker & Performance Marketing Lead", 
            "Search Engine Optimization (SEO), Google Ads (PPC), Meta Ads Management, CRO, Google Analytics 4", 
            "Digital Marketing", 
            6, 
            "Data-driven performance marketer specializing in low-CAC user acquisition funnels, technical SEO turnarounds, and creative conversion rate experiments.", 
            "https://chloedubois-growth.com", 
            1300.0, "Available", 4.9, 29
        )
    ]

    cursor.executemany("""
        INSERT INTO freelancer_profiles 
        (user_id, headline, skills, category, experience, bio, portfolio_url, hourly_rate, availability, rating_avg, rating_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, freelancer_profiles)

    # 3. Insert Fixed-Price Services (14 diverse packages covering multiple domains)
    services_data = [
        # (freelancer_id, title, description, category, price, delivery_days, deliverables, revisions, status, image_url)
        (
            6,
            "Complete Brand Identity & Modern Vector Logo Suite",
            "Get an iconic, timeless, and scalable brand identity. Includes 3 unique logo concepts, full vector source assets, typography system, color harmony guidelines, and ready-to-use social brand kits.",
            "Design",
            1499.0,
            3,
            "3 Custom Logo Concepts, High-Resolution PNG & JPG, Transparent Background, Source Vector File (AI/SVG/EPS), Brand Style Guide PDF, Social Media Avatar Kit",
            3,
            "Active",
            "https://images.unsplash.com/photo-1626785774573-4b799315345d?w=600&auto=format&fit=crop&q=80"
        ),
        (
            6,
            "High-Fidelity Mobile App UI/UX Prototype (Figma)",
            "Comprehensive UX design and pixel-perfect UI screens designed in Figma with full component library, reusable auto-layouts, and clickable prototype.",
            "Design",
            4999.0,
            5,
            "6 High-Fidelity UI Screens, Complete Figma Design System File, Interactive Clickable Prototype, SVG Icon Package, Developer Handover Documentation",
            3,
            "Active",
            "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=600&auto=format&fit=crop&q=80"
        ),
        (
            5,
            "Production-Grade Python Flask REST API & SQLite Database",
            "Secure, clean-coded RESTful API backend built with Python Flask, SQLite/PostgreSQL models, token authentication, error handlers, and Swagger documentation.",
            "Development",
            3499.0,
            4,
            "Modular Flask Backend Codebase, Database Migration Scripts, Postman Test Collection, OpenAPI / Swagger Docs, Automated Unit Test Suite",
            2,
            "Active",
            "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=600&auto=format&fit=crop&q=80"
        ),
        (
            5,
            "Ultra-Fast Responsive Landing Page in HTML5, CSS3 & Vanilla JS",
            "Blazing fast, 100/100 Google Lighthouse score landing page crafted with semantic HTML5, modern CSS3 animations, and interactive lead capture form.",
            "Development",
            2499.0,
            2,
            "Single Page Responsive Codebase, Cross-Browser Tested, Contact Form Script, SEO Meta Tags Pre-configured, Mobile Optimized",
            2,
            "Active",
            "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?w=600&auto=format&fit=crop&q=80"
        ),
        (
            7,
            "In-Depth Technical SEO Blog Post (1,500+ Words)",
            "Deeply researched, developer-focused technical article with code snippets, diagrams, meta descriptions, and targeted keyword search intent.",
            "Writing",
            999.0,
            2,
            "1,500+ Words Formatted Markdown, Focus Keyword Integration, Meta Title & Description, Copyscape Clean Report, Free Stock Illustration Selection",
            2,
            "Active",
            "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=600&auto=format&fit=crop&q=80"
        ),
        (
            8,
            "Cross-Platform MVP Mobile App with Flutter & Firebase",
            "Fully functional iOS and Android mobile MVP application containing 4 core screens, authentication flow, offline SQLite storage, and cloud synchronization.",
            "Mobile Apps",
            7999.0,
            7,
            "Clean Flutter Codebase (iOS & Android), Firebase Auth Integration, Production APK Build, Setup & Build Documentation",
            3,
            "Active",
            "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=600&auto=format&fit=crop&q=80"
        ),
        (
            9,
            "Custom RAG Pipeline Setup with LangChain & OpenAI",
            "Connect your private documents (PDFs, docs, tables) to an LLM via vector embeddings (Pinecone/Chroma) for hallucinations-free conversational QA.",
            "AI & Data Science",
            6499.0,
            5,
            "Python RAG Microservice, Document Chunking Script, Vector Database Indexing, Evaluation Benchmark Script, API Endpoint",
            2,
            "Active",
            "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&auto=format&fit=crop&q=80"
        ),
        (
            10,
            "Dockerization & Automated GitHub Actions CI/CD Pipeline",
            "Package your application into multi-stage optimized Docker containers and configure automated test-and-deploy workflows directly to AWS/DigitalOcean.",
            "DevOps & Cloud",
            2999.0,
            3,
            "Multi-stage Dockerfile, docker-compose.yml, GitHub Actions Workflow YAML, Environment Config Guide, Deployment Smoke Tests",
            2,
            "Active",
            "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=600&auto=format&fit=crop&q=80"
        ),
        (
            11,
            "Solidity Smart Contract Development & Gas Optimization",
            "ERC-20, ERC-721, or custom staking contract written in Solidity with comprehensive Hardhat tests and gas usage profiling.",
            "Blockchain & Web3",
            5499.0,
            4,
            "Solidity Contract Source Code, 100% Test Coverage Script, Gas Optimization Report, Deploy Script to Testnet/Mainnet",
            2,
            "Active",
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=600&auto=format&fit=crop&q=80"
        ),
        (
            12,
            "Photorealistic 3D Product Animation (15-30s Full HD)",
            "Stunning, studio-grade 3D product showcase video with fluid camera rotations, dynamic lighting, realistic materials, and background audio.",
            "Video & Motion",
            4499.0,
            5,
            "1080p 60fps MP4 Video Render, Blender 3D Source Project File, Licensed Background Sound Effects, 3 High-Res Still Renders",
            2,
            "Active",
            "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=80"
        ),
        (
            13,
            "Comprehensive Web Application Security & OWASP Audit",
            "Exhaustive vulnerability assessment of your web endpoints, authentication controls, and SQL/XSS vectors with prioritized remediation steps.",
            "Cybersecurity",
            5999.0,
            4,
            "Executive Summary PDF, Technical Vulnerability Log with Proof-of-Concepts, Code Remediation Snippets, 30-min Verification Retest",
            1,
            "Active",
            "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&auto=format&fit=crop&q=80"
        ),
        (
            14,
            "Interactive Executive Power BI / Tableau Dashboard",
            "Connect multiple data streams into an intuitive, filterable visual dashboard tracking revenue, customer acquisition cost, and churn metrics.",
            "Business & Analytics",
            3999.0,
            4,
            "Power BI / Tableau Workbook, Cleaned Data Model & DAX Queries, Mobile-Friendly View Layout, Executive User Guide PDF",
            2,
            "Active",
            "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=80"
        ),
        (
            15,
            "Playable 3D Game Prototype in Unity Engine",
            "Complete core gameplay mechanic, player controller, polished physics, sound triggers, and test arena for desktop or mobile.",
            "Game Development",
            6999.0,
            6,
            "Full Unity Project Source (C# scripts), Windows / Android Executable Build, Sound Effect Integration, Game Architecture Guide",
            2,
            "Active",
            "https://images.unsplash.com/photo-1552824722-ddab1374e622?w=600&auto=format&fit=crop&q=80"
        ),
        (
            16,
            "Complete Google Ads PPC & Conversion Tracking Setup",
            "Targeted search campaigns, negative keywords list, conversion pixel tracking, and compelling ad copy designed to maximize ROAS.",
            "Digital Marketing",
            2499.0,
            3,
            "3 Structured Ad Campaigns, Negative Keyword List (200+), GA4 Conversion Event Tracking, Ad Copy Variants, 7-Day Optimization Plan",
            2,
            "Active",
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&auto=format&fit=crop&q=80"
        )
    ]

    cursor.executemany("""
        INSERT INTO services 
        (freelancer_id, title, description, category, price, delivery_days, deliverables, revisions, status, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, services_data)

    # 4. Insert Client Requests (Requirement Board)
    client_requests_data = [
        (
            1,
            2,
            "Bespoke Multi-Vendor Campus Placement Portal",
            "We are seeking an experienced developer to create a web portal where students can submit resumes and recruiters can schedule interviews. We would like to consult on the architecture and discuss timelines.",
            "Development",
            "Python, Flask, SQLite, HTML5, Bootstrap 5",
            12000.0, 18000.0, "2026-11-20", "Open"
        ),
        (
            2,
            3,
            "Complete Brand Identity & Packaging for Organic Tea",
            "Looking for an artistic brand designer to craft eco-friendly packaging, label stickers, and social media templates for an artisanal tea brand launch.",
            "Design",
            "Packaging Design, Figma, Illustrator, Brand Kit",
            6000.0, 10000.0, "2026-11-15", "Open"
        ),
        (
            3,
            4,
            "Generative AI Chatbot for Internal HR Policy Answering",
            "Looking for an AI engineer to index 150+ employee handbook PDFs with vector search and build an internal query widget for our intranet.",
            "AI & Data Science",
            "LangChain, PyTorch, OpenAI API, Vector DB, Python",
            15000.0, 25000.0, "2026-11-30", "Open"
        ),
        (
            4,
            2,
            "Security Penetration Testing for Fintech Web Portal",
            "Pre-launch compliance audit required to verify OWASP vulnerabilities, token security, and database isolation before SOC2 certification.",
            "Cybersecurity",
            "OWASP Top 10, Penetration Testing, Python, Network Security",
            8000.0, 14000.0, "2026-11-18", "Open"
        )
    ]

    cursor.executemany("""
        INSERT INTO client_requests 
        (request_id, client_id, title, description, category, required_skills, budget_min, budget_max, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, client_requests_data)

    # 5. Insert Client Request Interests
    cursor.execute("""
        INSERT INTO client_request_interests (request_id, freelancer_id, message, status)
        VALUES (1, 5, 'I have previously built university placement portals with Flask and SQLite. Would love to schedule a consultation!', 'Interested')
    """)
    cursor.execute("""
        INSERT INTO client_request_interests (request_id, freelancer_id, message, status)
        VALUES (3, 9, 'I specialize in enterprise RAG systems with LangChain and vector databases. Let us review the architecture.', 'Interested')
    """)

    # 6. Insert Consultation (Model A Scenario)
    cursor.execute("""
        INSERT INTO consultations 
        (consultation_id, client_id, freelancer_id, request_title, project_description, preferred_datetime, meeting_type, meeting_link, notes, status)
        VALUES (1, 2, 5, 'Custom E-Commerce Platform Architecture', 'We need a bespoke multi-vendor store with admin analytics and order management. Let us discuss the exact deliverables and milestone costs.', '2026-11-04 15:00', 'Online', 'https://meet.google.com/xyz-abcd-efg', 'Discussion completed. Vikram prepared custom proposal.', 'Accepted')
    """)

    # 7. Insert Proposal History (Negotiation Flow)
    cursor.execute("""
        INSERT INTO proposals 
        (proposal_id, consultation_id, sender_id, proposed_amount, delivery_days, scope, message, version, status)
        VALUES (1, 1, 5, 15000.0, 10, 'Full responsive website with 5 core modules, SQLite database, admin panel, and payment gateway integration stubs.', 'Initial proposal as discussed in our consultation call.', 1, 'Superseded')
    """)
    cursor.execute("""
        INSERT INTO proposals 
        (proposal_id, consultation_id, sender_id, proposed_amount, delivery_days, scope, message, version, status)
        VALUES (2, 1, 2, 12000.0, 7, 'Trim down scope to 4 core modules without advanced payment gateway stubs.', 'We have a tighter budget for Phase 1. Can we streamline scope?', 2, 'Superseded')
    """)
    cursor.execute("""
        INSERT INTO proposals 
        (proposal_id, consultation_id, sender_id, proposed_amount, delivery_days, scope, message, version, status)
        VALUES (3, 1, 5, 13000.0, 8, 'Agreed scope: 4 core modules, clean SQLite models, responsive frontend, and deployment instructions.', 'Counter-offer accepted at ₹13,000 with 8-day turnaround.', 3, 'Accepted')
    """)

    # 8. Insert Custom Booking spawned from Accepted Proposal
    cursor.execute("""
        INSERT INTO bookings 
        (booking_id, client_id, freelancer_id, service_id, proposal_id, booking_type, agreed_amount, start_date, delivery_date, requirements, deliverable_notes, status)
        VALUES (1, 2, 5, NULL, 3, 'Custom', 13000.0, '2026-11-01', '2026-11-09', 'Develop 4-module e-commerce portal following accepted proposal v3.', 'Initial sprint completed. Database schema and auth endpoints deployed.', 'In Progress')
    """)

    # 9. Insert Fixed-Price Booking (Model B Scenario) - Completed with Review
    cursor.execute("""
        INSERT INTO bookings 
        (booking_id, client_id, freelancer_id, service_id, proposal_id, booking_type, agreed_amount, start_date, delivery_date, requirements, deliverable_notes, status)
        VALUES (2, 3, 6, 1, NULL, 'Fixed', 1499.0, '2026-10-25', '2026-10-28', 'Need minimalist logo for Organic Green Tea brand named "PureLeaf". Primary colors: Olive Green & Ivory.', 'Deliverable files packaged with source vector files (AI, SVG, EPS) and brand guidelines PDF.', 'Completed')
    """)

    # 10. Insert 10+ Diverse Verified Client Reviews
    reviews_data = [
        # (review_id, booking_id, client_id, freelancer_id, rating, comment)
        (1, 2, 3, 6, 5, "Ananya delivered beyond our expectations! The logo concepts were exceptional and captured our eco-friendly brand vision on the very first draft. Highly recommended!"),
    ]
    cursor.executemany("""
        INSERT INTO reviews (review_id, booking_id, client_id, freelancer_id, rating, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    """, reviews_data)

    # Add more completed bookings to support reviews for the showcase carousel
    extra_bookings_reviews = [
        (3, 4, 5, 3, None, 'Fixed', 3499.0, '2026-10-15', '2026-10-19', 'Flask REST API setup', 'REST API and Postman collection delivered.', 'Completed',
         5, "Vikram is a true Python master! The API is clean, blazingly fast, and completely documented."),
        (4, 2, 7, 5, None, 'Fixed', 999.0, '2026-10-18', '2026-10-20', 'SEO tech blog post', 'Article delivered with code snippets.', 'Completed',
         5, "Rohan's article ranked on page 1 of Google in just 10 days! Exceptional technical depth."),
        (5, 3, 8, 6, None, 'Fixed', 7999.0, '2026-10-10', '2026-10-17', 'Flutter MVP app', 'Android APK build and source code delivered.', 'Completed',
         5, "Neha built our mobile app seamlessly. 60fps animations and offline sync worked out of the box."),
        (6, 4, 9, 7, None, 'Fixed', 6499.0, '2026-10-12', '2026-10-17', 'RAG AI pipeline', 'RAG pipeline with LangChain delivered.', 'Completed',
         5, "Dr. Aakash solved our hallucination problems completely. The vector indexing is rock-solid."),
        (7, 2, 10, 8, None, 'Fixed', 2999.0, '2026-10-20', '2026-10-23', 'Docker CI/CD setup', 'GitHub Actions workflow deployed.', 'Completed',
         5, "Marcus reduced our cloud deployment time from 45 minutes to 3 minutes with zero downtime."),
        (8, 3, 11, 9, None, 'Fixed', 5499.0, '2026-10-05', '2026-10-09', 'Solidity contract', 'Gas-optimized contract delivered.', 'Completed',
         5, "Elena identified 2 critical gas optimization improvements that saved us thousands in deploy costs."),
        (9, 4, 12, 10, None, 'Fixed', 4499.0, '2026-10-02', '2026-10-07', '3D product animation', 'Full HD render delivered.', 'Completed',
         5, "Tariq's 3D animation became the centerpiece of our Kickstarter launch video. Pure cinema quality!"),
        (10, 2, 13, 11, None, 'Fixed', 5999.0, '2026-10-08', '2026-10-12', 'Security audit', 'Penetration test report delivered.', 'Completed',
         5, "Sarah found two subtle authentication logic flaws before our enterprise audit. Invaluable security expertise."),
        (11, 3, 14, 12, None, 'Fixed', 3999.0, '2026-10-14', '2026-10-18', 'Power BI Dashboard', 'Executive dashboard delivered.', 'Completed',
         5, "Maya transformed our messy spreadsheets into a dynamic executive dashboard that our board loves.")
    ]

    for b_id, cl_id, fl_id, s_id, p_id, b_type, amt, s_dt, d_dt, req, notes, st, stars, comm in extra_bookings_reviews:
        cursor.execute("""
            INSERT INTO bookings 
            (booking_id, client_id, freelancer_id, service_id, proposal_id, booking_type, agreed_amount, start_date, delivery_date, requirements, deliverable_notes, status, escrow_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Released')
        """, (b_id, cl_id, fl_id, s_id, p_id, b_type, amt, s_dt, d_dt, req, notes, st))

        cursor.execute("""
            INSERT INTO reviews (review_id, booking_id, client_id, freelancer_id, rating, comment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (b_id, b_id, cl_id, fl_id, stars, comm))

    # Update booking #1 and #2 with explicit escrow_status
    cursor.execute("UPDATE bookings SET escrow_status = 'Escrow_Locked' WHERE booking_id = 1;")
    cursor.execute("UPDATE bookings SET escrow_status = 'Released' WHERE booking_id = 2;")

    # Seed Wallets, UPI Transactions, and Milestones
    _seed_wallets_and_transactions(conn)

    conn.commit()
    conn.close()
    print("Database seeded successfully with 14+ talent profiles, 14+ services, 10+ reviews, and UPI Escrow Ledger.")

def _seed_wallets_and_transactions(conn):
    """Seed user wallets, realistic UPI transactions with 12-digit bank UTRs, and project milestones."""
    cursor = conn.cursor()
    # 1. Wallets for all users
    cursor.execute("SELECT user_id, full_name, email, role FROM users")
    users = cursor.fetchall()
    for u in users:
        u_id = u['user_id']
        u_role = u['role']
        u_name = u['full_name']
        cursor.execute("SELECT wallet_id FROM user_wallets WHERE user_id = ?", (u_id,))
        if not cursor.fetchone():
            default_upi = f"{u_name.lower().replace(' ', '').replace('.', '')}@okhdfcbank" if u_role == 'freelancer' else ""
            cursor.execute("SELECT COALESCE(SUM(agreed_amount), 0) FROM bookings WHERE freelancer_id = ? AND status = 'Completed'", (u_id,))
            earned = float(cursor.fetchone()[0])
            cursor.execute("SELECT COALESCE(SUM(agreed_amount), 0) FROM bookings WHERE freelancer_id = ? AND status IN ('Accepted', 'In Progress', 'Delivered')", (u_id,))
            in_escrow = float(cursor.fetchone()[0])
            cursor.execute("""
                INSERT INTO user_wallets (user_id, available_balance, escrow_balance, total_earned, payout_upi_id)
                VALUES (?, ?, ?, ?, ?)
            """, (u_id, earned, in_escrow, earned, default_upi))

    # 2. Seed Transactions for existing bookings if empty
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT * FROM bookings")
        bookings = cursor.fetchall()
        for b in bookings:
            b_id = b['booking_id']
            amt = b['agreed_amount']
            c_id = b['client_id']
            f_id = b['freelancer_id']
            st = b['status']
            if st == 'Completed':
                # Completed: Deposit then Release
                utr_dep = f"43098{b_id:04d}01"
                utr_rel = f"43098{b_id:04d}99"
                cursor.execute("""
                    INSERT INTO transactions 
                    (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, completed_at)
                    VALUES (?, ?, ?, ?, 'Escrow_Deposit', 'UPI_QR', 'freelanceconnect.escrow@icici', 'client@okhdfcbank', ?, 'Escrow_Locked', 'Secured in Escrow Trust via Phone UPI', ?)
                """, (b_id, c_id, f_id, amt, utr_dep, b['created_at']))
                cursor.execute("""
                    INSERT INTO transactions 
                    (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, completed_at)
                    VALUES (?, ?, ?, ?, 'Escrow_Release', 'UPI', 'freelanceconnect.escrow@icici', 'freelanceconnect.escrow@icici', ?, 'Released', 'Client verified delivery & released funds to freelancer', ?)
                """, (b_id, c_id, f_id, amt, utr_rel, b['created_at']))
            elif st in ['Accepted', 'In Progress', 'Delivered']:
                utr_dep = f"43098{b_id:04d}55"
                cursor.execute("""
                    INSERT INTO transactions 
                    (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, completed_at)
                    VALUES (?, ?, ?, ?, 'Escrow_Deposit', 'UPI_QR', 'freelanceconnect.escrow@icici', 'client@okhdfcbank', ?, 'Escrow_Locked', '100% Escrow Guarantee locked via Phone UPI', ?)
                """, (b_id, c_id, f_id, amt, utr_dep, b['created_at']))

    # 3. Seed sample milestones for Booking #1 (Custom project)
    cursor.execute("SELECT COUNT(*) FROM project_milestones WHERE booking_id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO project_milestones (booking_id, title, amount, status, delivery_date, notes)
            VALUES 
            (1, 'Phase 1: Architecture & Auth Endpoints', 4000.0, 'Approved_Released', '2026-11-04', 'Database schema, JWT auth, and admin seeds deployed.'),
            (1, 'Phase 2: Core E-Commerce & Catalog API', 5000.0, 'Funded_Escrow', '2026-11-07', 'Product listings, search filters, and shopping cart logic.'),
            (1, 'Phase 3: Checkout, Payment Testing & Deployment', 4000.0, 'Funded_Escrow', '2026-11-09', 'Full UPI payment simulator, admin moderation, and live staging.')
        """)
    conn.commit()

if __name__ == '__main__':
    seed_db(force=True)
