import hashlib
import logging

logger = logging.getLogger(__name__)


def subscribe_email(
    email: str,
    api_key: str,
    list_id: str,
    server_prefix: str,
    tags: list = None,
) -> dict:
    """
    Add or update a subscriber in a Mailchimp audience.

    Uses a PUT (upsert) so re-submitting the same email is safe.
    Tags the subscriber with ["rsu-vitals-lead"] by default.

    Returns {"success": True} or {"success": False, "error": str}.
    """
    if not api_key or not list_id:
        return {"success": False, "error": "Mailchimp credentials not configured."}

    if tags is None:
        tags = ["rsu-vitals-lead"]

    try:
        import mailchimp_marketing as MailchimpMarketing
        from mailchimp_marketing.api_client import ApiClientError

        client = MailchimpMarketing.Client()
        client.set_config({"api_key": api_key, "server": server_prefix})

        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()

        client.lists.set_list_member(
            list_id,
            subscriber_hash,
            {
                "email_address": email,
                "status_if_new": "subscribed",
                "tags": [{"name": t, "status": "active"} for t in tags],
            },
        )
        return {"success": True}

    except Exception as e:
        logger.error("Mailchimp subscribe error: %s", e)
        return {"success": False, "error": str(e)}
