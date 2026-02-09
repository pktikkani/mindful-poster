"""
Scheduler for automated daily post generation.

Runs the content generation pipeline on a schedule (default: 7 AM IST daily).
Generates a post via Claude API and sends an approval email to Nitesh.
"""

import threading

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from .generator import generate_post
from .emailer import send_approval_email


def daily_generate_and_email():
    """Generate a new post and send it for approval."""
    print("\n🧘 Daily generation triggered...")

    try:
        # Generate the post
        post_data = generate_post()
        print(f"✅ Generated post #{post_data['post_id']}: {post_data.get('hook', '')[:60]}...")

        # Send approval email
        send_approval_email(post_data)
        print(f"📧 Approval email sent for post #{post_data['post_id']}")

    except Exception as e:
        print(f"❌ Daily generation failed: {e}")
        # In production, you'd want to send an error notification here
        import traceback
        traceback.print_exc()


def start_scheduler():
    """Start the APScheduler with the configured schedule."""
    settings = get_settings()
    scheduler = BlockingScheduler()

    trigger = CronTrigger(
        hour=settings.post_generation_hour,
        minute=settings.post_generation_minute,
        timezone=settings.timezone,
    )

    scheduler.add_job(
        daily_generate_and_email,
        trigger=trigger,
        id="daily_post_generation",
        name="Generate daily mindfulness post",
        replace_existing=True,
    )

    print(
        f"⏰ Scheduler started! Posts will be generated daily at "
        f"{settings.post_generation_hour:02d}:{settings.post_generation_minute:02d} "
        f"({settings.timezone})"
    )
    print("Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹️ Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
