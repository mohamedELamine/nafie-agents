import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("supervisor.resend_client")


class ResendClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def send_owner_alert(self, subject: str, message: str, to: Optional[str] = None) -> bool:
        """Send alert to owner"""
        try:
            import resend

            email = to or "admin@yourdomain.com"

            response = resend.Emails.send(
                {
                    "from": "Supervisor <no-reply@yourdomain.com>",
                    "to": [email],
                    "subject": subject,
                    "text": message,
                }
            )

            logger.info(f"Sent owner alert: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending owner alert: {e}")
            raise

    async def send_critical_system_alert(
        self, alert_type: str, details: dict, to: Optional[str] = None, retry: int = 3
    ) -> bool:
        """Send critical system alert with retry logic"""
        attempts = 0

        while attempts < retry:
            try:
                import resend

                email = to or "admin@yourdomain.com"
                subject = f"CRITICAL: {alert_type}"

                html_content = f"""
                <html>
                <body>
                    <h2 style="color: red;">{alert_type}</h2>
                    <p><strong>Details:</strong></p>
                    <pre style="background: #f5f5f5; padding: 10px;">{json.dumps(details, indent=2)}</pre>
                    <p>Time: {datetime.utcnow().isoformat()}</p>
                </body>
                </html>
                """

                response = resend.Emails.send(
                    {
                        "from": "Supervisor <no-reply@yourdomain.com>",
                        "to": [email],
                        "subject": subject,
                        "html": html_content,
                    }
                )

                logger.warning(f"Sent critical alert ({attempts + 1}/{retry}): {alert_type}")
                return True

            except Exception as e:
                attempts += 1
                logger.error(f"Critical alert failed (attempt {attempts}/{retry}): {e}")

                if attempts >= retry:
                    logger.error(f"Critical alert failed after {retry} attempts: {alert_type}")
                    return False

        return False

    async def send_workflow_notification(
        self, workflow_type: str, status: str, workflow_id: str, details: dict
    ) -> bool:
        """Send workflow status notification"""
        try:
            import resend

            email = "admin@yourdomain.com"

            subject = f"Workflow Update: {workflow_type} - {status}"
            message = f"""
            Workflow: {workflow_type}
            Status: {status}
            Workflow ID: {workflow_id}
            Time: {datetime.utcnow().isoformat()}

            Details:
            {json.dumps(details, indent=2)}
            """

            response = resend.Emails.send(
                {
                    "from": "Supervisor <no-reply@yourdomain.com>",
                    "to": [email],
                    "subject": subject,
                    "text": message,
                }
            )

            return True

        except Exception as e:
            logger.error(f"Error sending workflow notification: {e}")
            return False
