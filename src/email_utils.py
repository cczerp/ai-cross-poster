"""
Email utility functions for sending confirmation emails
"""
import os
import secrets
from flask import url_for
from flask_mail import Message
from threading import Thread


def generate_verification_token():
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)


def send_verification_email(mail, user_email, username, token, app):
    """
    Send email verification email to user
    
    Args:
        mail: Flask-Mail instance
        user_email: User's email address
        username: User's username
        token: Verification token
        app: Flask app instance (for generating URLs)
    """
    with app.app_context():
        # Generate verification URL
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        
        # Email subject and body
        subject = "Verify Your Resell Rebel Account"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #4CAF50 0%, #2196F3 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: #4CAF50;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .button:hover {{
                    background: #45a049;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Resell Rebel!</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>Thank you for signing up! Please verify your email address to complete your registration.</p>
                    <p style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #2196F3;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© Resell Rebel - Inventory Management Made Easy</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to Resell Rebel!
        
        Hi {username},
        
        Thank you for signing up! Please verify your email address by clicking the link below:
        
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account, you can safely ignore this email.
        
        © Resell Rebel
        """
        
        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body,
            body=text_body
        )
        
        try:
            mail.send(msg)
            print(f"✅ Verification email sent to {user_email}")
            return True
        except Exception as e:
            print(f"❌ Failed to send verification email to {user_email}: {e}")
            return False


def send_verification_email_async(mail, user_email, username, token, app):
    """Send verification email asynchronously"""
    thread = Thread(target=send_verification_email, args=(mail, user_email, username, token, app))
    thread.daemon = True
    thread.start()
    return thread
