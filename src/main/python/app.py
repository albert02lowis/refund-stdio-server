from flask import Flask, request, jsonify
import datetime
import uuid
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Email configuration
# Note: Replace these with your actual SMTP settings
SMTP_SERVER = "smtp.gmail.com"  # Gmail SMTP server
SMTP_PORT = 587  # Port for TLS
SMTP_USERNAME = os.environ.get('REFUND_SMTP_EMAIL')  # Your Gmail address
SMTP_PASSWORD = os.environ.get('REFUND_SMTP_PASSWORD')  # Your app password (not your Gmail password)
SENDER_EMAIL = "refundpy@example.com"  # Sender email address

# In-memory database for demonstration purposes
purchases_db = [
    {
        "id": "p001",
        "customer_email": SMTP_USERNAME,
        "product": "Wireless Headphones",
        "amount": 89.99,
        "purchase_date": "2025-04-15",
        "status": "completed"
    },
    {
        "id": "p002",
        "customer_email": "sarah@example.com",
        "product": "Smart Watch",
        "amount": 199.99,
        "purchase_date": "2025-04-18",
        "status": "completed"
    },
    {
        "id": "p003",
        "customer_email": "mike@example.com",
        "product": "Bluetooth Speaker",
        "amount": 59.99,
        "purchase_date": "2025-04-20",
        "status": "completed"
    },
    {
        "id": "p004",
        "customer_email": SMTP_USERNAME,
        "product": "Fancy Coat",
        "amount": 299.99,
        "purchase_date": "2025-04-20",
        "status": "completed"
    },
]

refunds_db = []

def send_email(recipient, subject, message):
    """Send an email using configured SMTP server"""
    try:
        # Create a multipart message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject

        # Add body to email
        msg.attach(MIMEText(message, "plain"))

        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Send email
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False

@app.route('/')
def home():
    return "Refund API Server is running!"

@app.route('/api/listPurchases', methods=['GET'])
def list_purchases():
    email = request.args.get('email')
    if email:
        filtered_purchases = [p for p in purchases_db if p['customer_email'] == email]
        return jsonify({"purchases": filtered_purchases, "count": len(filtered_purchases)})
    else:
        return jsonify({"purchases": purchases_db, "count": len(purchases_db)})

@app.route('/api/requestRefund', methods=['POST'])
def request_refund():
    data = request.json
    purchase_id = data.get('purchase_id')
    reason = data.get('reason')
    print(f"request_refund: {str(data)}")

    # Validate input
    if not purchase_id or not reason:
        return jsonify({"success": False, "error": "Missing purchase_id or reason"}), 400

    # Find the purchase
    purchase = next((p for p in purchases_db if p['id'] == purchase_id), None)
    if not purchase:
        return jsonify({"success": False, "error": "Purchase not found"}), 404

    # Check if purchase is refundable (example condition: not already refunded)
    if purchase['status'] == 'refunded':
        return jsonify({"success": False, "error": "Purchase already refunded"}), 400

    # Process refund request
    refund_id = f"r{str(uuid.uuid4())[:8]}"
    refund = {
        "id": refund_id,
        "purchase_id": purchase_id,
        "reason": reason,
        "status": "pending",
        "request_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "customer_email": purchase["customer_email"]
    }

    refunds_db.append(refund)

    # Update purchase status
    purchase['status'] = 'refund_pending'

    # Create a response with both refund and purchase details
    response = {
        "success": True,
        "message": "Refund request submitted",
        "refund": {
            "id": refund_id,
            "status": "pending",
            "reason": reason,
            "request_date": refund["request_date"]
        },
        "purchase": {
            "id": purchase["id"],
            "product": purchase["product"],
            "amount": purchase["amount"],
            "purchase_date": purchase["purchase_date"],
            "customer_email": purchase["customer_email"],
            "status": purchase["status"]
        }
    }

    return jsonify(response)

@app.route('/api/sendRefundCompleteEmail', methods=['POST'])
def send_refund_complete_email():
    data = request.json
    refund_id = data.get('refund_id')
    override_email = data.get('email')  # Optional email override
    print(f"send_refund_complete_email: {str(data)}")

    # Validate input
    if not refund_id:
        return jsonify({"success": False, "error": "Missing refund_id"}), 400

    # Find the refund
    refund = next((r for r in refunds_db if r['id'] == refund_id), None)
    if not refund:
        return jsonify({"success": False, "error": "Refund not found"}), 404

    # Find associated purchase
    purchase = next((p for p in purchases_db if p['id'] == refund['purchase_id']), None)
    if not purchase:
        return jsonify({"success": False, "error": "Associated purchase not found"}), 404

    # Determine recipient email
    recipient_email = override_email if override_email else refund['customer_email']

    # Prepare email content
    subject = f"Your refund for {purchase['product']} has been processed"
    message = f"""
    Dear Customer,

    Your refund request for {purchase['product']} (Order ID: {purchase['id']}) has been processed successfully.

    Refund Details:
    - Amount: ${purchase['amount']}
    - Date Processed: {datetime.datetime.now().strftime("%Y-%m-%d")}
    - Reason: {refund['reason']}

    The refund should appear in your account within 3-5 business days, depending on your payment provider.

    If you have any questions, please contact our customer support team.

    Thank you for your patience.

    Best regards,
    The Support Team
    """

    # Send actual email
    email_sent = send_email(recipient_email, subject, message)

    # Update statuses
    if email_sent:
        refund['status'] = 'completed'
        purchase['status'] = 'refunded'

        return jsonify({
            "success": True,
            "message": f"Refund complete email sent to {recipient_email}",
            "refund_status": refund['status'],
            "purchase": purchase
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to send email",
            "refund_status": refund['status']
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)