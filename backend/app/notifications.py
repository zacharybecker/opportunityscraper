import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select

from app.config import settings
from app.db import async_session
from app.models import (
    NotificationLog,
    NotificationRule,
    Opportunity,
    OpportunityAnalysis,
    ScrapeRun,
    User,
)

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via SMTP."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured, skipping email")
        return False

    try:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg.set_content(body, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=True,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


async def send_webhook(url: str, payload: dict, secret: str = "") -> bool:
    """Send a webhook with HMAC signature."""
    try:
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}

        if secret:
            signature = hmac.new(
                secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, content=body, headers=headers)
            response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Webhook failed for {url}: {e}")
        return False


async def log_notification(
    rule_id: Optional[str],
    user_id: str,
    channel: str,
    subject: str,
    body: str,
    status: str,
    opportunity_id: Optional[str] = None,
):
    """Log a notification to the database."""
    async with async_session() as db:
        log_entry = NotificationLog(
            rule_id=rule_id,
            user_id=user_id,
            channel=channel,
            subject=subject,
            body=body,
            status=status,
            opportunity_id=opportunity_id,
        )
        db.add(log_entry)
        await db.commit()


async def check_scrape_notifications(run_id: str):
    """Check notification rules after a scrape completes."""
    async with async_session() as db:
        # Get the run
        run_result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == run_id))
        run = run_result.scalar_one_or_none()
        if not run:
            return

        # Get all enabled notification rules
        rules_result = await db.execute(
            select(NotificationRule).where(NotificationRule.is_enabled == True)
        )
        rules = rules_result.scalars().all()

        for rule in rules:
            try:
                if rule.trigger_type == "scrape_complete":
                    await fire_notification(rule, {
                        "event": "scrape_complete",
                        "scraper_id": str(run.scraper_config_id),
                        "stats": run.stats,
                    })
                elif rule.trigger_type == "scrape_failed" and run.status == "failed":
                    await fire_notification(rule, {
                        "event": "scrape_failed",
                        "scraper_id": str(run.scraper_config_id),
                        "error": run.error_message,
                    })
            except Exception as e:
                logger.error(f"Error checking rule {rule.id}: {e}")


async def check_analysis_notifications(opportunity_id: str):
    """Check notification rules after an analysis completes."""
    async with async_session() as db:
        # Get analysis
        analysis_result = await db.execute(
            select(OpportunityAnalysis).where(
                OpportunityAnalysis.opportunity_id == opportunity_id
            )
        )
        analysis = analysis_result.scalar_one_or_none()
        if not analysis:
            return

        # Get opportunity
        opp_result = await db.execute(
            select(Opportunity).where(Opportunity.id == opportunity_id)
        )
        opp = opp_result.scalar_one_or_none()
        if not opp:
            return

        # Check rules
        rules_result = await db.execute(
            select(NotificationRule).where(NotificationRule.is_enabled == True)
        )
        rules = rules_result.scalars().all()

        for rule in rules:
            try:
                if rule.trigger_type == "high_relevancy" and analysis.relevancy_label == "high":
                    min_score = rule.conditions.get("min_score", 80)
                    if analysis.relevancy_score and float(analysis.relevancy_score) >= min_score:
                        await fire_notification(rule, {
                            "event": "high_relevancy",
                            "opportunity_title": opp.title,
                            "opportunity_id": str(opp.id),
                            "relevancy_score": float(analysis.relevancy_score),
                            "agency": opp.agency,
                        }, opportunity_id=str(opp.id))
                elif rule.trigger_type == "new_opportunity":
                    await fire_notification(rule, {
                        "event": "new_opportunity",
                        "opportunity_title": opp.title,
                        "opportunity_id": str(opp.id),
                        "agency": opp.agency,
                        "naics": opp.naics_code,
                    }, opportunity_id=str(opp.id))
            except Exception as e:
                logger.error(f"Error checking analysis rule {rule.id}: {e}")


async def send_deadline_reminders(opportunities: list):
    """Send deadline reminder notifications."""
    async with async_session() as db:
        rules_result = await db.execute(
            select(NotificationRule).where(
                NotificationRule.is_enabled == True,
                NotificationRule.trigger_type == "deadline_approaching",
            )
        )
        rules = rules_result.scalars().all()

        for rule in rules:
            for opp in opportunities:
                try:
                    days_left = (opp.response_deadline - datetime.now(timezone.utc)).days
                    await fire_notification(rule, {
                        "event": "deadline_approaching",
                        "opportunity_title": opp.title,
                        "opportunity_id": str(opp.id),
                        "deadline": opp.response_deadline.isoformat(),
                        "days_remaining": days_left,
                    }, opportunity_id=str(opp.id))
                except Exception as e:
                    logger.error(f"Error sending deadline reminder: {e}")


async def fire_notification(
    rule: NotificationRule,
    payload: dict,
    opportunity_id: Optional[str] = None,
):
    """Fire a notification through configured channels."""
    channels = rule.channels or []

    # Get user email
    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.id == rule.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return

    subject = f"OpportunityScraper: {payload.get('event', 'Notification')}"

    # Build email body
    body = build_email_body(payload)

    for channel in channels:
        status = "failed"
        if channel == "email":
            to_email = rule.email_override or user.email
            if to_email:
                success = await send_email(to_email, subject, body)
                status = "sent" if success else "failed"
        elif channel == "webhook":
            if rule.webhook_url:
                success = await send_webhook(rule.webhook_url, payload)
                status = "sent" if success else "failed"

        await log_notification(
            rule_id=str(rule.id),
            user_id=str(rule.user_id),
            channel=channel,
            subject=subject,
            body=body,
            status=status,
            opportunity_id=opportunity_id,
        )


def build_email_body(payload: dict) -> str:
    """Build a simple HTML email body from notification payload."""
    event = payload.get("event", "notification")

    html = f"""<html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #228be6;">OpportunityScraper Alert</h2>
<p><strong>Event:</strong> {event.replace('_', ' ').title()}</p>
"""

    if "opportunity_title" in payload:
        html += f'<p><strong>Opportunity:</strong> {payload["opportunity_title"]}</p>'
    if "agency" in payload:
        html += f'<p><strong>Agency:</strong> {payload["agency"]}</p>'
    if "relevancy_score" in payload:
        html += f'<p><strong>Relevancy Score:</strong> {payload["relevancy_score"]}%</p>'
    if "deadline" in payload:
        html += f'<p><strong>Deadline:</strong> {payload["deadline"]}</p>'
    if "days_remaining" in payload:
        html += f'<p><strong>Days Remaining:</strong> {payload["days_remaining"]}</p>'
    if "stats" in payload:
        stats = payload["stats"]
        html += f'<p><strong>Results:</strong> Found: {stats.get("found", 0)}, New: {stats.get("new", 0)}, Updated: {stats.get("updated", 0)}</p>'
    if "error" in payload:
        html += f'<p style="color: red;"><strong>Error:</strong> {payload["error"]}</p>'

    html += "</body></html>"
    return html
