import os
import logging

logger = logging.getLogger("visual_production.resend_client")


class ResendClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def send_visual_review_request(
        self,
        to_email: str,
        batch_id: str,
        theme_slug: str,
        version: str,
        assets: list,
        total_cost: float,
    ) -> bool:
        """Send visual review request email"""
        try:
            # Build HTML content
            html_content = f"""
            <html>
            <body>
                <h2>Visual Assets Review Request</h2>
                <p>Theme: <strong>{theme_slug}</strong></p>
                <p>Version: <strong>{version}</strong></p>
                <p>Batch ID: <strong>{batch_id}</strong></p>
                <p>Total Cost: ${total_cost:.2f}</p>
                <p><a href="/review/{batch_id}">Review Assets</a></p>
                <h3>Assets:</h3>
                <ul>
            """

            for asset in assets:
                html_content += f"""
                    <li>
                        <strong>{asset["type"]}</strong>: {asset["url"]}
                        <br>Status: {asset["status"]}
                    </li>
                """

            html_content += """
                </ul>
                <p>Please review and approve or reject the assets.</p>
            </body>
            </html>
            """

            # Send email
            import resend

            response = resend.Emails.send(
                {
                    "from": f"Visual Production <{os.environ.get('RESEND_FROM_EMAIL', 'no-reply@example.com')}>",
                    "to": [to_email],
                    "subject": f"Visual Assets Review: {theme_slug} v{version}",
                    "html": html_content,
                }
            )

            logger.info(f"Sent visual review request to {to_email} for batch {batch_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending visual review request: {e}")
            raise

    async def send_batch_failed_alert(
        self, to_email: str, batch_id: str, error_message: str, theme_slug: str
    ) -> bool:
        """Send batch failure alert"""
        try:
            html_content = f"""
            <html>
            <body>
                <h2>Visual Production Batch Failed</h2>
                <p>Theme: <strong>{theme_slug}</strong></p>
                <p>Batch ID: <strong>{batch_id}</strong></p>
                <p>Error: <strong>{error_message}</strong></p>
                <p>Please investigate and retry.</p>
            </body>
            </html>
            """

            import resend

            response = resend.Emails.send(
                {
                    "from": f"Visual Production <{os.environ.get('RESEND_FROM_EMAIL', 'no-reply@example.com')}>",
                    "to": [to_email],
                    "subject": f"Visual Production Failed: {batch_id}",
                    "html": html_content,
                }
            )

            logger.error(f"Sent batch failure alert to {to_email} for batch {batch_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending batch failure alert: {e}")
            raise

    async def send_batch_complete(
        self,
        to_email: str,
        batch_id: str,
        theme_slug: str,
        approved_count: int,
        rejected_count: int,
    ) -> bool:
        """Send batch completion notification"""
        try:
            html_content = f"""
            <html>
            <body>
                <h2>Visual Assets Batch Completed</h2>
                <p>Theme: <strong>{theme_slug}</strong></p>
                <p>Batch ID: <strong>{batch_id}</strong></p>
                <p>Approved: {approved_count}</p>
                <p>Rejected: {rejected_count}</p>
                <p>Assets are now ready for deployment.</p>
            </body>
            </html>
            """

            import resend

            response = resend.Emails.send(
                {
                    "from": f"Visual Production <{os.environ.get('RESEND_FROM_EMAIL', 'no-reply@example.com')}>",
                    "to": [to_email],
                    "subject": f"Visual Assets Batch Completed: {batch_id}",
                    "html": html_content,
                }
            )

            logger.info(f"Sent batch completion notification to {to_email} for batch {batch_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending batch completion notification: {e}")
            raise
