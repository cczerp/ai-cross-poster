"""
Notification Manager
====================
Handles all notifications: sales, offers, failures, price alerts.

Supports:
- Email notifications
- In-app notifications
- Push notifications (future)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database import get_db


class NotificationManager:
    """
    Manages all notifications for the cross-poster.

    Features:
    - Email alerts for sales (with shipping labels)
    - Email alerts for offers
    - Email alerts for listing failures
    - Price drop alerts
    - In-app notification storage
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None,
    ):
        """
        Initialize notification manager.

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port (587 for TLS, 465 for SSL)
            smtp_username: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            to_email: Recipient email address
        """
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT", "587"))
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("NOTIFICATION_FROM_EMAIL")
        self.to_email = to_email or os.getenv("NOTIFICATION_TO_EMAIL")

        self.db = get_db()

        # Check if email is configured
        self.email_enabled = all([
            self.smtp_username,
            self.smtp_password,
            self.from_email,
            self.to_email,
        ])

    def _send_email(
        self,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> bool:
        """
        Send an email notification.

        Args:
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body (optional)
            attachments: List of (filename, file_data) tuples

        Returns:
            True if sent successfully
        """
        if not self.email_enabled:
            print("⚠️  Email notifications not configured (check .env)")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = self.to_email

            # Add text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)

            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

            # Add attachments
            if attachments:
                for filename, file_data in attachments:
                    attachment = MIMEApplication(file_data)
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=filename
                    )
                    msg.attach(attachment)

            # Send email
            if self.smtp_port == 465:
                # SSL
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            else:
                # TLS (port 587)
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)

            return True

        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False

    def send_sale_notification(
        self,
        listing_id: int,
        platform: str,
        sale_price: float,
        listing_title: str,
        buyer_email: Optional[str] = None,
        tracking_number: Optional[str] = None,
        shipping_label_path: Optional[str] = None,
    ):
        """
        Send notification when item sells.

        Args:
            listing_id: Database listing ID
            platform: Platform where it sold
            sale_price: Final sale price
            listing_title: Title of listing
            buyer_email: Buyer email (for shipping label)
            tracking_number: Shipping tracking number
            shipping_label_path: Path to shipping label PDF
        """
        # Get listing details
        listing = self.db.get_listing(listing_id)
        if not listing:
            return

        # Calculate profit
        cost = listing.get("cost", 0) or 0
        profit = sale_price - cost
        profit_margin = (profit / sale_price * 100) if sale_price > 0 else 0

        # Get storage location
        storage_location = listing.get("storage_location")

        # Create in-app notification
        notification_data = {
            "platform": platform,
            "sale_price": sale_price,
            "cost": cost,
            "profit": profit,
            "profit_margin": profit_margin,
            "buyer_email": buyer_email,
            "tracking_number": tracking_number,
            "storage_location": storage_location,
        }

        # Build message with storage location prominently
        message = f"{listing_title} sold for ${sale_price:.2f}"
        if storage_location:
            message += f" | 📍 Location: {storage_location}"

        notification_id = self.db.create_notification(
            type="sale",
            listing_id=listing_id,
            platform=platform,
            title=f"🎉 Item Sold on {platform}!",
            message=message,
            data=notification_data,
        )

        print(f"\n{'='*70}")
        print(f"🎉 SALE NOTIFICATION")
        print(f"{'='*70}")
        print(f"Item: {listing_title}")
        print(f"Platform: {platform}")
        print(f"Sale Price: ${sale_price:.2f}")

        # Show storage location prominently
        if storage_location:
            print(f"\n📍 STORAGE LOCATION: {storage_location}")
            print(f"   Go to {storage_location} to find and ship this item!\n")

        if cost > 0:
            print(f"Cost: ${cost:.2f}")
            print(f"Profit: ${profit:.2f} ({profit_margin:.1f}%)")
        if tracking_number:
            print(f"Tracking: {tracking_number}")
        print(f"{'='*70}\n")

        # Send email
        if self.email_enabled:
            subject = f"🎉 Sale Alert: {listing_title}"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #28a745;">🎉 Congratulations! Your item sold!</h2>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">{listing_title}</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td><strong>Platform:</strong></td>
                            <td>{platform}</td>
                        </tr>
                        <tr>
                            <td><strong>Sale Price:</strong></td>
                            <td style="color: #28a745; font-size: 1.2em;">${sale_price:.2f}</td>
                        </tr>
                        {"<tr><td><strong>Your Cost:</strong></td><td>$" + f"{cost:.2f}</td></tr>" if cost > 0 else ""}
                        {"<tr><td><strong>Profit:</strong></td><td style='color: " + ("green" if profit > 0 else "red") + f"; font-weight: bold;'>${profit:.2f} ({profit_margin:.1f}%)</td></tr>" if cost > 0 else ""}
                        {"<tr><td><strong>Buyer Email:</strong></td><td>" + buyer_email + "</td></tr>" if buyer_email else ""}
                        {"<tr><td><strong>Tracking:</strong></td><td>" + tracking_number + "</td></tr>" if tracking_number else ""}
                    </table>
                </div>

                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <strong>Next Steps:</strong>
                    <ul>
                        <li>Pack the item securely</li>
                        <li>Print the shipping label ({"attached" if shipping_label_path else "download from " + platform})</li>
                        <li>Ship within 1-2 business days</li>
                        <li>Update tracking info</li>
                    </ul>
                </div>

                <p style="color: #6c757d; font-size: 0.9em; margin-top: 30px;">
                    This listing has been automatically removed from all other platforms.
                </p>
            </body>
            </html>
            """

            text_body = f"""
            SALE ALERT!

            Your item sold: {listing_title}

            Platform: {platform}
            Sale Price: ${sale_price:.2f}
            {"Cost: $" + f"{cost:.2f}" if cost > 0 else ""}
            {"Profit: $" + f"{profit:.2f} ({profit_margin:.1f}%)" if cost > 0 else ""}
            {"Buyer: " + buyer_email if buyer_email else ""}
            {"Tracking: " + tracking_number if tracking_number else ""}

            Next steps:
            - Pack item securely
            - Print shipping label
            - Ship within 1-2 business days
            """

            # Attach shipping label if provided
            attachments = []
            if shipping_label_path and os.path.exists(shipping_label_path):
                with open(shipping_label_path, "rb") as f:
                    label_data = f.read()
                    attachments.append((f"shipping_label_{listing_id}.pdf", label_data))

            email_sent = self._send_email(subject, html_body, text_body, attachments if attachments else None)

            if email_sent:
                self.db.mark_notification_emailed(notification_id)
                print("✅ Sale notification email sent")
            else:
                print("⚠️  Failed to send email notification")

    def send_offer_notification(
        self,
        listing_id: int,
        platform: str,
        offer_amount: float,
        buyer_name: Optional[str] = None,
        listing_title: Optional[str] = None,
    ):
        """
        Send notification when someone makes an offer.

        Args:
            listing_id: Database listing ID
            platform: Platform where offer was made
            offer_amount: Offer amount
            buyer_name: Name of buyer
            listing_title: Title of listing
        """
        listing = self.db.get_listing(listing_id)
        if not listing:
            return

        if not listing_title:
            listing_title = listing["title"]

        asking_price = listing["price"]
        offer_percentage = (offer_amount / asking_price * 100) if asking_price > 0 else 0

        # Create notification
        notification_data = {
            "platform": platform,
            "offer_amount": offer_amount,
            "asking_price": asking_price,
            "offer_percentage": offer_percentage,
            "buyer_name": buyer_name,
        }

        notification_id = self.db.create_notification(
            type="offer",
            listing_id=listing_id,
            platform=platform,
            title=f"💰 New Offer on {platform}",
            message=f"${offer_amount:.2f} offer on {listing_title}",
            data=notification_data,
        )

        print(f"\n{'='*70}")
        print(f"💰 NEW OFFER")
        print(f"{'='*70}")
        print(f"Item: {listing_title}")
        print(f"Platform: {platform}")
        print(f"Offer: ${offer_amount:.2f} ({offer_percentage:.0f}% of asking price)")
        print(f"Asking: ${asking_price:.2f}")
        if buyer_name:
            print(f"Buyer: {buyer_name}")
        print(f"{'='*70}\n")

        # Send email
        if self.email_enabled:
            subject = f"💰 New Offer: ${offer_amount:.2f} on {listing_title}"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #007bff;">💰 You have a new offer!</h2>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">{listing_title}</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td><strong>Platform:</strong></td>
                            <td>{platform}</td>
                        </tr>
                        <tr>
                            <td><strong>Offer Amount:</strong></td>
                            <td style="color: #007bff; font-size: 1.2em;">${offer_amount:.2f}</td>
                        </tr>
                        <tr>
                            <td><strong>Your Asking Price:</strong></td>
                            <td>${asking_price:.2f}</td>
                        </tr>
                        <tr>
                            <td><strong>Offer is:</strong></td>
                            <td style="font-weight: bold;">{offer_percentage:.0f}% of asking price</td>
                        </tr>
                        {"<tr><td><strong>From:</strong></td><td>" + buyer_name + "</td></tr>" if buyer_name else ""}
                    </table>
                </div>

                <p><strong>Review and respond to this offer on {platform}.</strong></p>
            </body>
            </html>
            """

            text_body = f"""
            NEW OFFER!

            {listing_title}

            Platform: {platform}
            Offer: ${offer_amount:.2f}
            Asking: ${asking_price:.2f}
            Offer is: {offer_percentage:.0f}% of asking price
            {"From: " + buyer_name if buyer_name else ""}

            Review and respond on {platform}.
            """

            email_sent = self._send_email(subject, html_body, text_body)

            if email_sent:
                self.db.mark_notification_emailed(notification_id)
                print("✅ Offer notification email sent")

    def send_listing_failed_notification(
        self,
        listing_id: int,
        platform: str,
        error: str,
        listing_title: str,
    ):
        """
        Send notification when listing fails to post.

        Args:
            listing_id: Database listing ID
            platform: Platform where posting failed
            error: Error message
            listing_title: Title of listing
        """
        # Create notification
        notification_data = {
            "platform": platform,
            "error": error,
        }

        notification_id = self.db.create_notification(
            type="listing_failed",
            listing_id=listing_id,
            platform=platform,
            title=f"❌ Listing Failed on {platform}",
            message=f"Failed to post: {listing_title}",
            data=notification_data,
        )

        print(f"\n{'='*70}")
        print(f"❌ LISTING FAILURE ALERT")
        print(f"{'='*70}")
        print(f"Item: {listing_title}")
        print(f"Platform: {platform}")
        print(f"Error: {error}")
        print(f"{'='*70}\n")

        # Send email
        if self.email_enabled:
            subject = f"❌ Listing Failed on {platform}"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc3545;">❌ Listing Failed</h2>

                <div style="background: #f8d7da; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                    <h3 style="margin-top: 0; color: #721c24;">{listing_title}</h3>
                    <p><strong>Platform:</strong> {platform}</p>
                    <p><strong>Error:</strong></p>
                    <pre style="background: white; padding: 10px; border-radius: 4px; overflow-x: auto;">{error}</pre>
                </div>

                <p>The system will automatically retry this listing. You can also manually retry from the dashboard.</p>
            </body>
            </html>
            """

            text_body = f"""
            LISTING FAILED

            {listing_title}

            Platform: {platform}
            Error: {error}

            The system will automatically retry this listing.
            """

            email_sent = self._send_email(subject, html_body, text_body)

            if email_sent:
                self.db.mark_notification_emailed(notification_id)
                print("✅ Failure notification email sent")

    def send_price_alert(
        self,
        collectible_id: int,
        collectible_name: str,
        target_price: float,
        current_price: float,
        source: str = "market_scan",
    ):
        """
        Send notification when collectible hits target price.

        Args:
            collectible_id: Database collectible ID
            collectible_name: Name of collectible
            target_price: Your target price
            current_price: Current market price
            source: Where price was found
        """
        # Create notification
        notification_data = {
            "collectible_id": collectible_id,
            "target_price": target_price,
            "current_price": current_price,
            "source": source,
            "savings": target_price - current_price,
        }

        notification_id = self.db.create_notification(
            type="price_alert",
            listing_id=None,
            platform=None,
            title=f"🔔 Price Alert: {collectible_name}",
            message=f"Now ${current_price:.2f} (target: ${target_price:.2f})",
            data=notification_data,
        )

        savings = target_price - current_price
        savings_pct = (savings / target_price * 100) if target_price > 0 else 0

        print(f"\n{'='*70}")
        print(f"🔔 PRICE ALERT")
        print(f"{'='*70}")
        print(f"Collectible: {collectible_name}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Your Target: ${target_price:.2f}")
        print(f"Savings: ${savings:.2f} ({savings_pct:.0f}%)")
        print(f"Source: {source}")
        print(f"{'='*70}\n")

        # Send email
        if self.email_enabled:
            subject = f"🔔 Price Alert: {collectible_name} - ${current_price:.2f}"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #28a745;">🔔 Price Alert!</h2>

                <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="margin-top: 0; color: #155724;">{collectible_name}</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td><strong>Current Price:</strong></td>
                            <td style="color: #28a745; font-size: 1.3em; font-weight: bold;">${current_price:.2f}</td>
                        </tr>
                        <tr>
                            <td><strong>Your Target:</strong></td>
                            <td>${target_price:.2f}</td>
                        </tr>
                        <tr>
                            <td><strong>You Save:</strong></td>
                            <td style="color: #28a745; font-weight: bold;">${savings:.2f} ({savings_pct:.0f}%)</td>
                        </tr>
                        <tr>
                            <td><strong>Source:</strong></td>
                            <td>{source}</td>
                        </tr>
                    </table>
                </div>

                <p><strong>This collectible is now at or below your target price!</strong></p>
            </body>
            </html>
            """

            text_body = f"""
            PRICE ALERT!

            {collectible_name}

            Current Price: ${current_price:.2f}
            Your Target: ${target_price:.2f}
            You Save: ${savings:.2f} ({savings_pct:.0f}%)
            Source: {source}

            This collectible is now at or below your target price!
            """

            email_sent = self._send_email(subject, html_body, text_body)

            if email_sent:
                self.db.mark_notification_emailed(notification_id)
                print("✅ Price alert email sent")

    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        notifications = self.db.get_unread_notifications()
        return len(notifications)

    def get_recent_notifications(self, limit: int = 10) -> List[Dict]:
        """Get recent notifications"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM notifications
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    @classmethod
    def from_env(cls) -> "NotificationManager":
        """Create notification manager from environment variables"""
        return cls(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            from_email=os.getenv("NOTIFICATION_FROM_EMAIL"),
            to_email=os.getenv("NOTIFICATION_TO_EMAIL"),
        )
