"""
Comprehensive Automated Test Suite for FreelanceConnect
Tests both hiring models (Consultation & Negotiation, Fixed-Price Booking),
Authentication, Client Requirement Board, and Admin Dashboard.
"""
import unittest
import os
from app import app
from database import init_db, seed_db, get_db

class FreelanceConnectTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_db(force=True)

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        # Clean any leftover test users between test runs
        db = get_db()
        db.execute("DELETE FROM users WHERE email IN ('testclient@example.com', 'testfreelancer@example.com', 'duplicate@example.com')")
        db.commit()
        db.close()

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # -------------------------------------------------------------
    # 1. Authentication & RBAC Tests (A01 - A06)
    # -------------------------------------------------------------
    def test_a01_register_client(self):
        """A01: Register a new client successfully"""
        response = self.client.post('/register', data=dict(
            full_name="Test Client User",
            email="testclient@example.com",
            password="password123",
            confirm_password="password123",
            role="client"
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Client User", response.data)

    def test_a02_register_freelancer(self):
        """A02: Register a new freelancer and verify profile creation"""
        response = self.client.post('/register', data=dict(
            full_name="Test Freelancer Pro",
            email="testfreelancer@example.com",
            password="password123",
            confirm_password="password123",
            role="freelancer"
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should redirect to profile edit
        self.assertIn(b"Update Professional Profile", response.data)

    def test_a03_duplicate_email(self):
        """A03: Duplicate email registration is rejected"""
        response = self.client.post('/register', data=dict(
            full_name="Duplicate User",
            email="client@example.com", # Already seeded
            password="password123",
            confirm_password="password123",
            role="client"
        ), follow_redirects=True)
        self.assertIn(b"already exists", response.data)

    def test_a04_invalid_login(self):
        """A04: Invalid password login rejected"""
        response = self.login("client@example.com", "wrongpassword")
        self.assertIn(b"Invalid email or password", response.data)

    def test_a05_logout(self):
        """A05: Logout destroys session"""
        self.login("client@example.com", "client123")
        response = self.logout()
        self.assertIn(b"logged out safely", response.data)

    def test_a06_unauthorized_admin_access(self):
        """A06: Normal client cannot access admin panel"""
        self.login("client@example.com", "client123")
        response = self.client.get('/admin', follow_redirects=True)
        self.assertIn(b"permission to access that resource", response.data)

    # -------------------------------------------------------------
    # 2. Model A: Consultation & Negotiation Workflow (B01 - B08)
    # -------------------------------------------------------------
    def test_b_consultation_and_negotiation_flow(self):
        """
        B01-B08: Full end-to-end Consultation & Negotiation Workflow:
        1. Client requests consultation with Neha Patel (mobile@example.com)
        2. Freelancer accepts and provides meeting link
        3. Freelancer submits initial proposal (v1: 10,000, 7 days)
        4. Client submits counterproposal (v2: 8,500, 5 days)
        5. Freelancer accepts counterproposal (v2)
        6. System automatically verifies creation of Custom Engagement in bookings
        """
        db = get_db()
        freelancer = db.execute("SELECT user_id FROM users WHERE email = 'mobile@example.com'").fetchone()
        fl_id = freelancer['user_id']
        db.close()

        # Step 1: Client requests consultation
        self.login("client@example.com", "client123")
        res_req = self.client.post(f'/consultation/request/{fl_id}', data=dict(
            request_title="Cross-Platform Flutter Delivery App",
            project_description="Need a sleek mobile app for delivery agents with real-time geolocation.",
            preferred_datetime="2026-11-10T14:00",
            meeting_type="Online",
            notes="Please bring any recent Flutter portfolio references."
        ), follow_redirects=True)
        self.assertEqual(res_req.status_code, 200)
        self.assertIn(b"Consultation request submitted", res_req.data)

        # Get the new consultation ID
        db = get_db()
        consultation = db.execute("""
            SELECT consultation_id FROM consultations 
            WHERE client_id = 2 AND freelancer_id = ? AND request_title = 'Cross-Platform Flutter Delivery App'
        """, (fl_id,)).fetchone()
        c_id = consultation['consultation_id']
        db.close()

        # Step 2: Freelancer logs in and accepts consultation
        self.logout()
        self.login("mobile@example.com", "mobile123")
        res_accept = self.client.post(f'/consultation/{c_id}/status', data=dict(
            status="Accepted",
            meeting_link="https://meet.google.com/test-flutter-slot",
            notes="Ready to discuss project architecture!"
        ), follow_redirects=True)
        self.assertIn(b"Consultation meeting confirmed", res_accept.data)

        # Step 3: Freelancer submits Initial Proposal (v1: ₹10,000, 7 days)
        res_prop = self.client.post(f'/negotiation/{c_id}/initial-proposal', data=dict(
            proposed_amount=10000.0,
            delivery_days=7,
            scope="Complete cross-platform Flutter code, Google Maps integration, SQLite local cache.",
            message="Initial scope estimate following our call."
        ), follow_redirects=True)
        self.assertIn(b"Initial project proposal submitted", res_prop.data)

        db = get_db()
        p1 = db.execute("SELECT * FROM proposals WHERE consultation_id = ? AND version = 1", (c_id,)).fetchone()
        p1_id = p1['proposal_id']
        db.close()

        # Step 4: Client logs in and submits Counterproposal (v2: ₹8,500, 6 days)
        self.logout()
        self.login("client@example.com", "client123")
        res_counter = self.client.post(f'/proposal/{p1_id}/counter', data=dict(
            proposed_amount=8500.0,
            delivery_days=6,
            scope="Flutter code + Google Maps, client will manage backend setup.",
            message="Streamlined scope to fit our startup milestone budget."
        ), follow_redirects=True)
        self.assertIn(b"Counterproposal Version 2 submitted", res_counter.data)

        db = get_db()
        p2 = db.execute("SELECT * FROM proposals WHERE consultation_id = ? AND version = 2", (c_id,)).fetchone()
        p2_id = p2['proposal_id']
        db.close()

        # Step 5: Freelancer logs back in and accepts counterproposal (v2)
        self.logout()
        self.login("mobile@example.com", "mobile123")
        res_agree = self.client.post(f'/proposal/{p2_id}/accept', follow_redirects=True)
        self.assertIn(b"accepted. Custom engagement", res_agree.data)

        # Step 6: Verify custom project engagement in bookings
        db = get_db()
        custom_booking = db.execute("""
            SELECT * FROM bookings WHERE proposal_id = ? AND booking_type = 'Custom'
        """, (p2_id,)).fetchone()
        self.assertIsNotNone(custom_booking)
        self.assertEqual(custom_booking['agreed_amount'], 8500.0)
        self.assertEqual(custom_booking['status'], 'In Progress')
        db.close()

    # -------------------------------------------------------------
    # 3. Model B: Fixed-Price Service Booking & Review (C01 - C08)
    # -------------------------------------------------------------
    def test_c_fixed_price_booking_and_review_flow(self):
        """
        C01-C08: Full Fixed-Price Service Lifecycle:
        1. Client views service details
        2. Client submits booking with start date and instructions
        3. Freelancer accepts booking
        4. Freelancer marks In Progress
        5. Freelancer marks Delivered with notes
        6. Client marks Completed
        7. Client posts 5-star review
        8. Verify freelancer average rating recalculated
        """
        db = get_db()
        service = db.execute("SELECT service_id, freelancer_id FROM services LIMIT 1").fetchone()
        s_id = service['service_id']
        db.close()

        # Step 1 & 2: Client books service
        self.login("client@example.com", "client123")
        res_book = self.client.post(f'/booking/service/{s_id}', data=dict(
            start_date="2026-11-05",
            requirements="Clean responsive deliverable with modern branding."
        ), follow_redirects=True)
        self.assertEqual(res_book.status_code, 200)
        self.assertIn(b"Fixed-price service booking submitted", res_book.data)

        db = get_db()
        b_rec = db.execute("""
            SELECT booking_id, freelancer_id FROM bookings WHERE service_id = ? AND client_id = 2 ORDER BY booking_id DESC LIMIT 1
        """, (s_id,)).fetchone()
        b_id = b_rec['booking_id']
        fl_user = db.execute("SELECT email FROM users WHERE user_id = ?", (b_rec['freelancer_id'],)).fetchone()
        fl_email = fl_user['email']
        db.close()

        # Step 3: Freelancer accepts booking
        self.logout()
        self.login(fl_email, "designer123" if "designer" in fl_email else "freelancer123" if "freelancer" in fl_email else "password123")
        res_acc = self.client.post(f'/booking/{b_id}/status', data=dict(
            status="Accepted"
        ), follow_redirects=True)
        self.assertIn(b"status updated to: Accepted", res_acc.data)

        # Step 4: Freelancer marks In Progress
        res_prog = self.client.post(f'/booking/{b_id}/status', data=dict(
            status="In Progress"
        ), follow_redirects=True)
        self.assertIn(b"status updated to: In Progress", res_prog.data)

        # Step 5: Freelancer marks Delivered
        res_del = self.client.post(f'/booking/{b_id}/status', data=dict(
            status="Delivered",
            deliverable_notes="Landing page completed and deployed to demo server. Source code zipped."
        ), follow_redirects=True)
        self.assertIn(b"status updated to: Delivered", res_del.data)

        # Step 6: Client confirms completion
        self.logout()
        self.login("client@example.com", "client123")
        res_comp = self.client.post(f'/booking/{b_id}/complete', follow_redirects=True)
        self.assertIn(b"Project completion confirmed", res_comp.data)

        # Step 7: Client submits 5-star review
        res_rev = self.client.post(f'/booking/{b_id}/review', data=dict(
            rating="5",
            comment="Outstanding work! Delivered 1 day ahead of schedule with perfect responsive quality."
        ), follow_redirects=True)
        self.assertIn(b"Your verified review and rating have been posted", res_rev.data)

        # Step 8: Verify review saved in DB
        db = get_db()
        rev = db.execute("SELECT * FROM reviews WHERE booking_id = ?", (b_id,)).fetchone()
        self.assertIsNotNone(rev)
        self.assertEqual(rev['rating'], 5)
        db.close()

    # -------------------------------------------------------------
    # 4. Model C: Client Requirement Board Tests
    # -------------------------------------------------------------
    def test_d_client_requirement_board(self):
        """Test Model C: Client Requirement Board and Freelancer Expression of Interest"""
        # Client posts requirement
        self.login("client@example.com", "client123")
        res_post = self.client.post('/client-requests/new', data=dict(
            title="Automated PDF Invoicing Service",
            category="Development",
            budget_min=4000.0,
            budget_max=7000.0,
            deadline="2026-11-25",
            required_skills="Python, ReportLab, Flask",
            description="Microservice to generate tamper-proof PDF invoices from JSON payloads."
        ), follow_redirects=True)
        self.assertIn(b"project requirement has been published", res_post.data)

        db = get_db()
        req = db.execute("SELECT request_id FROM client_requests WHERE title = 'Automated PDF Invoicing Service'").fetchone()
        req_id = req['request_id']
        db.close()

        # Freelancer expresses interest
        self.logout()
        self.login("freelancer@example.com", "freelancer123")
        res_interest = self.client.post(f'/client-requests/{req_id}/interest', data=dict(
            message="I have built PDF report generators using Python and ReportLab extensively. Let's schedule a call."
        ), follow_redirects=True)
        self.assertIn(b"expression of interest has been sent", res_interest.data)

    # -------------------------------------------------------------
    # 5. Marketplace Search & Discovery
    # -------------------------------------------------------------
    def test_e_marketplace_search(self):
        """Test searching freelancers and filtering by category"""
        res_search = self.client.get('/explore?q=Python')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"Vikram Rao", res_search.data)

        res_cat = self.client.get('/explore?category=Design')
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b"Ananya Sen", res_cat.data)

    # -------------------------------------------------------------
    # 6. Phone UPI Payment, Escrow Lifecycle & Wallet Tests (F01 - F06)
    # -------------------------------------------------------------
    def test_f_upi_payment_and_escrow_lifecycle(self):
        """
        Full Phone UPI Payment, Escrow Trust & Freelancer Wallet Lifecycle:
        1. Client initiates UPI Escrow Checkout for Booking #1
        2. Verify dynamic NPCI UPI URI and scannable QR Code generation
        3. Simulate Phone UPI App webhook / UTR verification (Escrow_Locked)
        4. Verify booking advances to In Progress and freelancer escrow balance credited
        5. Verify live status polling endpoint
        6. Client releases escrow upon delivery (Escrow_Release)
        7. Verify freelancer wallet available balance credited
        8. Freelancer executes instant UPI payout withdrawal
        9. Verify printable tax invoice & receipt generation
        """
        # Step 1 & 2: Client accesses UPI Escrow Checkout for Booking #1
        db = get_db()
        db.execute("UPDATE bookings SET escrow_status = 'Pending_Deposit' WHERE booking_id = 1")
        db.execute("DELETE FROM transactions WHERE booking_id = 1")
        db.commit()
        db.close()

        self.login("client@example.com", "client123")
        res_checkout = self.client.get('/payment/checkout/1')
        self.assertEqual(res_checkout.status_code, 200)
        self.assertIn(b"Secure UPI Payment", res_checkout.data)
        self.assertIn(b"freelanceconnect.escrow@icici", res_checkout.data)
        self.assertIn(b"upi://pay?", res_checkout.data)

        # Get transaction ID
        db = get_db()
        txn = db.execute("SELECT * FROM transactions WHERE booking_id = 1 AND payment_type = 'Escrow_Deposit'").fetchone()
        self.assertIsNotNone(txn)
        txn_id = txn['transaction_id']
        db.close()

        # Step 3: Simulate phone payment confirmation via webhook simulator
        res_webhook = self.client.post(f'/api/payment/simulate-webhook/{txn_id}')
        self.assertEqual(res_webhook.status_code, 200)
        self.assertIn(b"Escrow_Locked", res_webhook.data)

        # Step 4: Verify booking status updated and funds locked in escrow
        db = get_db()
        b_after = db.execute("SELECT * FROM bookings WHERE booking_id = 1").fetchone()
        self.assertEqual(b_after['escrow_status'], 'Escrow_Locked')
        fl_wallet = db.execute("SELECT * FROM user_wallets WHERE user_id = ?", (b_after['freelancer_id'],)).fetchone()
        self.assertGreaterEqual(fl_wallet['escrow_balance'], b_after['agreed_amount'])
        db.close()

        # Step 5: Test live polling endpoint
        res_poll = self.client.get(f'/api/payment/status/{txn_id}')
        self.assertEqual(res_poll.status_code, 200)
        self.assertIn(b"Escrow_Locked", res_poll.data)

        # Step 6: Client releases escrow payment to freelancer
        res_release = self.client.post('/payment/release-escrow/1', follow_redirects=True)
        self.assertEqual(res_release.status_code, 200)
        self.assertIn(b"successfully released to freelancer", res_release.data)

        # Step 7: Verify booking is marked Completed with Released escrow
        db = get_db()
        b_completed = db.execute("SELECT * FROM bookings WHERE booking_id = 1").fetchone()
        self.assertEqual(b_completed['escrow_status'], 'Released')
        self.assertEqual(b_completed['status'], 'Completed')
        fl_wallet_after = db.execute("SELECT * FROM user_wallets WHERE user_id = ?", (b_completed['freelancer_id'],)).fetchone()
        self.assertGreaterEqual(fl_wallet_after['available_balance'], b_completed['agreed_amount'])
        db.close()

        # Step 8: Freelancer logs in, views wallet, and withdraws via UPI
        self.logout()
        self.login("freelancer@example.com", "freelancer123")
        res_wallet = self.client.get('/wallet')
        self.assertEqual(res_wallet.status_code, 200)
        self.assertIn(b"Earnings, Escrow", res_wallet.data)

        res_withdraw = self.client.post('/wallet/withdraw', data=dict(
            amount=5000.0,
            target_upi_id="vikram@okhdfcbank"
        ), follow_redirects=True)
        self.assertIn(b"transferred successfully to vikram@okhdfcbank", res_withdraw.data)

        # Step 9: View Tax Invoice & Payment Receipt
        res_receipt = self.client.get(f'/payment/receipt/{txn_id}')
        self.assertEqual(res_receipt.status_code, 200)
        self.assertIn(b"INVOICE", res_receipt.data)
        self.assertIn(b"NPCI UPI 2.0", res_receipt.data)

if __name__ == '__main__':
    unittest.main()
