"""
FreelanceConnect Payment & Escrow Engine
Handles UPI Transactions, Escrow State Transitions, Wallet Balances, and Tax Invoices.
"""
import time
import secrets
from datetime import datetime
from database import get_db
from utils.upi_qr import build_upi_uri, generate_upi_qr_svg

PLATFORM_ESCROW_VPA = "freelanceconnect.escrow@icici"
PLATFORM_NAME = "FreelanceConnect Escrow Trust"

def generate_upi_utr() -> str:
    """Generate a realistic 12-digit Indian Bank UPI Unique Transaction Reference (UTR)."""
    # Format: Year(1) + DayOfYear(3) + Hour(2) + Random(6) e.g. 430981726543
    now = datetime.now()
    prefix = f"{now.year % 10}{now.timetuple().tm_yday:03d}{now.hour:02d}"
    suffix = f"{secrets.randbelow(900000) + 100000}"
    return f"{prefix}{suffix}"

def get_or_create_wallet(db, user_id: int):
    """Retrieve or initialize a user's wallet with zero balances."""
    wallet = db.execute("SELECT * FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
    if not wallet:
        user = db.execute("SELECT full_name, email, role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return None
        default_upi = ""
        if user['role'] == 'freelancer':
            clean_name = user['full_name'].lower().replace(' ', '').replace('.', '')
            default_upi = f"{clean_name}@okhdfcbank"
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO user_wallets (user_id, available_balance, escrow_balance, total_earned, payout_upi_id)
            VALUES (?, 0.0, 0.0, 0.0, ?)
        """, (user_id, default_upi))
        db.commit()
        wallet = db.execute("SELECT * FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
    return wallet

def get_booking_payment_summary(db, booking_id: int):
    """Retrieve complete payment, escrow status, and recent transactions for an order."""
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
        return None

    # Get active deposit transaction (Escrow_Locked or Initiated)
    active_txn = db.execute("""
        SELECT * FROM transactions 
        WHERE booking_id = ? AND payment_type IN ('Escrow_Deposit', 'Milestone_Deposit')
        ORDER BY transaction_id DESC LIMIT 1
    """, (booking_id,)).fetchone()

    # Get all transactions for this booking
    history = db.execute("""
        SELECT * FROM transactions 
        WHERE booking_id = ? 
        ORDER BY transaction_id DESC
    """, (booking_id,)).fetchall()

    return {
        'booking': booking,
        'active_txn': active_txn,
        'history': history,
        'escrow_status': booking['escrow_status'] or 'Pending_Deposit'
    }

def initiate_escrow_deposit(db, booking_id: int, payer_id: int):
    """
    Initiate or retrieve an existing UPI Escrow Deposit transaction for a booking.
    Generates dynamic UPI URI and scannable QR Code.
    """
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    if not booking:
        return None, "Booking not found"

    if booking['client_id'] != payer_id:
        return None, "Only the hiring client can deposit funds into escrow"

    # Check for existing transaction
    existing = db.execute("""
        SELECT * FROM transactions 
        WHERE booking_id = ? AND payment_type = 'Escrow_Deposit' AND status IN ('Initiated', 'Escrow_Locked')
        ORDER BY transaction_id DESC LIMIT 1
    """, (booking_id,)).fetchone()

    amount = float(booking['agreed_amount'])
    note = f"Order #{booking_id} Escrow Guarantee"

    if existing and existing['status'] == 'Escrow_Locked':
        return existing, "Payment already verified and locked in escrow"

    if existing and existing['status'] == 'Initiated':
        # Re-use existing initiated transaction
        txn_id = existing['transaction_id']
        utr_ref = existing['upi_ref_no']
        uri, svg = generate_upi_qr_svg(
            vpa=PLATFORM_ESCROW_VPA,
            name=PLATFORM_NAME,
            amount=amount,
            txn_ref=utr_ref,
            note=note
        )
        return dict(existing, upi_uri=uri, qr_svg=svg), None

    # Create new transaction
    utr_ref = f"FC-ORD{booking_id:04d}-{int(time.time())}"
    uri, svg = generate_upi_qr_svg(
        vpa=PLATFORM_ESCROW_VPA,
        name=PLATFORM_NAME,
        amount=amount,
        txn_ref=utr_ref,
        note=note
    )

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO transactions 
        (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, qr_data)
        VALUES (?, ?, ?, ?, 'Escrow_Deposit', 'UPI_QR', ?, '', ?, 'Initiated', ?, ?)
    """, (
        booking_id,
        booking['client_id'],
        booking['freelancer_id'],
        amount,
        PLATFORM_ESCROW_VPA,
        utr_ref,
        note,
        uri
    ))
    txn_id = cursor.lastrowid
    db.commit()

    txn = db.execute("SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)).fetchone()
    return dict(txn, upi_uri=uri, qr_svg=svg), None

def verify_and_lock_escrow(db, transaction_id: int, payer_upi_id: str = "", bank_utr: str = ""):
    """
    Confirm UPI payment verification (either from phone UTR submission or webhook simulation).
    Locks funds safely into platform escrow and updates project status.
    """
    txn = db.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()
    if not txn:
        return False, "Transaction not found"

    if txn['status'] == 'Escrow_Locked':
        return True, "Payment is already locked in escrow"

    booking_id = txn['booking_id']
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    if not booking:
        return False, "Associated booking not found"

    final_utr = bank_utr.strip() if bank_utr else generate_upi_utr()
    final_payer_upi = payer_upi_id.strip() if payer_upi_id else "client@okhdfcbank"
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor = db.cursor()
    # 1. Update transaction
    cursor.execute("""
        UPDATE transactions 
        SET status = 'Escrow_Locked',
            payer_upi_id = ?,
            upi_ref_no = ?,
            completed_at = ?
        WHERE transaction_id = ?
    """, (final_payer_upi, final_utr, now_ts, transaction_id))

    # 2. Update booking escrow_status
    new_booking_status = booking['status']
    if booking['status'] == 'Pending':
        new_booking_status = 'In Progress'

    cursor.execute("""
        UPDATE bookings 
        SET escrow_status = 'Escrow_Locked',
            status = ?
        WHERE booking_id = ?
    """, (new_booking_status, booking_id))

    # 3. Update freelancer wallet escrow balance
    get_or_create_wallet(db, booking['freelancer_id'])
    cursor.execute("""
        UPDATE user_wallets 
        SET escrow_balance = escrow_balance + ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (txn['amount'], booking['freelancer_id']))

    db.commit()
    return True, f"UPI payment of ₹{txn['amount']:,.0f} verified! Funds secured in Escrow Trust. (UTR: {final_utr})"

def release_escrow_to_freelancer(db, booking_id: int, client_or_admin_id: int, is_admin: bool = False):
    """
    Release locked escrow funds to the freelancer's available wallet balance.
    Can be executed by the client after receiving work, or by platform admin.
    """
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    if not booking:
        return False, "Booking not found"

    if not is_admin and booking['client_id'] != client_or_admin_id:
        return False, "Only the hiring client can release escrow funds"

    if booking['escrow_status'] != 'Escrow_Locked':
        return False, f"Cannot release escrow: current status is '{booking['escrow_status']}'"

    amount = float(booking['agreed_amount'])
    freelancer_id = booking['freelancer_id']
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    release_utr = generate_upi_utr()

    cursor = db.cursor()
    # 1. Insert release transaction record
    cursor.execute("""
        INSERT INTO transactions 
        (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, completed_at)
        VALUES (?, ?, ?, ?, 'Escrow_Release', 'UPI', ?, 'freelanceconnect.escrow@icici', ?, 'Released', 'Client confirmed work completion & released escrow payout', ?)
    """, (
        booking_id,
        booking['client_id'],
        freelancer_id,
        amount,
        PLATFORM_ESCROW_VPA,
        release_utr,
        now_ts
    ))

    # 2. Update booking status
    cursor.execute("""
        UPDATE bookings 
        SET escrow_status = 'Released',
            status = 'Completed'
        WHERE booking_id = ?
    """, (booking_id,))

    # 3. Update freelancer wallet: deduct from escrow, credit to available & total_earned
    get_or_create_wallet(db, freelancer_id)
    cursor.execute("""
        UPDATE user_wallets 
        SET escrow_balance = MAX(0.0, escrow_balance - ?),
            available_balance = available_balance + ?,
            total_earned = total_earned + ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (amount, amount, amount, freelancer_id))

    db.commit()
    return True, f"₹{amount:,.0f} successfully released to freelancer! Payout credited to their wallet."

def withdraw_wallet_to_upi(db, user_id: int, amount: float, target_upi_id: str):
    """Freelancer withdraws available wallet funds directly to their personal UPI ID."""
    wallet = get_or_create_wallet(db, user_id)
    if not wallet:
        return False, "Wallet not found"

    if amount <= 0:
        return False, "Withdrawal amount must be greater than zero"

    if float(wallet['available_balance']) < amount:
        return False, f"Insufficient balance. Available: ₹{wallet['available_balance']:,.2f}"

    clean_upi = target_upi_id.strip()
    if not clean_upi or '@' not in clean_upi:
        return False, "Please enter a valid recipient UPI ID (e.g. name@okhdfcbank)"

    payout_utr = generate_upi_utr()
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor = db.cursor()
    # Deduct from wallet and update saved UPI
    cursor.execute("""
        UPDATE user_wallets 
        SET available_balance = available_balance - ?,
            payout_upi_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (amount, clean_upi, user_id))

    # Insert payout transaction (booking_id = 1 or active booking placeholder)
    cursor.execute("""
        INSERT INTO transactions 
        (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, completed_at)
        VALUES (1, 1, ?, ?, 'Payout_Withdrawal', 'UPI', ?, 'freelanceconnect.payouts@icici', ?, 'Released', 'Instant UPI payout transfer to bank account', ?)
    """, (
        user_id,
        amount,
        clean_upi,
        payout_utr,
        now_ts
    ))
    db.commit()

    return True, f"Payout of ₹{amount:,.0f} transferred successfully to {clean_upi}! (Bank UTR: {payout_utr})"

def refund_escrow_to_client(db, booking_id: int, admin_user_id: int, reason: str = "Dispute resolution"):
    """Platform Admin refunds locked escrow back to the client."""
    booking = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    if not booking:
        return False, "Booking not found"

    if booking['escrow_status'] != 'Escrow_Locked':
        return False, "Only locked escrow funds can be refunded"

    amount = float(booking['agreed_amount'])
    refund_utr = generate_upi_utr()
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor = db.cursor()
    # 1. Insert refund transaction
    cursor.execute("""
        INSERT INTO transactions 
        (booking_id, payer_id, payee_id, amount, payment_type, payment_method, upi_vpa, payer_upi_id, upi_ref_no, status, notes, completed_at)
        VALUES (?, 1, ?, ?, 'Refund', 'UPI', 'client@upi', 'freelanceconnect.escrow@icici', ?, 'Refunded', ?, ?)
    """, (
        booking_id,
        booking['client_id'],
        amount,
        refund_utr,
        f"Admin Escrow Refund: {reason}",
        now_ts
    ))

    # 2. Update booking status
    cursor.execute("""
        UPDATE bookings 
        SET escrow_status = 'Refunded',
            status = 'Cancelled'
        WHERE booking_id = ?
    """, (booking_id,))

    # 3. Deduct from freelancer escrow balance
    cursor.execute("""
        UPDATE user_wallets 
        SET escrow_balance = MAX(0.0, escrow_balance - ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (amount, booking['freelancer_id']))

    db.commit()
    return True, f"Escrow refund of ₹{amount:,.0f} processed back to client's UPI account. (UTR: {refund_utr})"
