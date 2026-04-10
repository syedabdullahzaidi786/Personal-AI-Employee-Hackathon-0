"""
WHATSAPP_BROADCAST_ACTION — Core Broadcast Engine
Sends the same message to N WhatsApp numbers via Playwright WhatsApp Web.
No Twilio. No API key. Uses your own WhatsApp account.

Usage::

    from golden_tier_external_world.actions.whatsapp.action import WhatsAppBroadcastAction
    from golden_tier_external_world.actions.whatsapp.models import WhatsAppBroadcastRequest

    action = WhatsAppBroadcastAction(session_dir="wa_session")
    req    = WhatsAppBroadcastRequest(
        to_numbers=["+923001234567", "+923009876543"],
        message="Hello from AI Employee!",
    )
    result = action.broadcast(req)
    print(result.sent, result.failed)
"""

from __future__ import annotations

import time
from typing import Optional

from .models import (
    WhatsAppBroadcastRequest,
    WhatsAppBroadcastResult,
    WhatsAppBroadcastStatus,
)


class WhatsAppBroadcastAction:
    """
    Broadcasts a single message to multiple WhatsApp numbers.

    Uses PlaywrightWhatsAppClient under the hood — browser launches once,
    sends to all numbers in sequence, then closes.

    Never raises — all errors captured in WhatsAppBroadcastResult.
    """

    def __init__(
        self,
        session_dir: str = "wa_session",
        vault_root:  str = "",
        delay_between_sends: float = 2.0,
    ) -> None:
        self._session_dir         = session_dir
        self._vault_root          = vault_root
        self._delay_between_sends = delay_between_sends

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def broadcast(self, req: WhatsAppBroadcastRequest) -> WhatsAppBroadcastResult:
        """
        Send req.message to all req.to_numbers.

        Returns WhatsAppBroadcastResult with per-number send status.
        Never raises.
        """
        if not req.to_numbers:
            return WhatsAppBroadcastResult(
                request_id=req.request_id,
                status=WhatsAppBroadcastStatus.FAILED,
                error="No phone numbers provided.",
            )

        client = self._make_client()

        try:
            if not client.launch():
                return WhatsAppBroadcastResult(
                    request_id=req.request_id,
                    status=WhatsAppBroadcastStatus.FAILED,
                    error="Playwright browser launch failed. Check playwright install.",
                )

            if not client.open_wa_web():
                return WhatsAppBroadcastResult(
                    request_id=req.request_id,
                    status=WhatsAppBroadcastStatus.FAILED,
                    error="WhatsApp Web login failed or timed out.",
                )

            sent:   list[str] = []
            failed: list[str] = []

            for i, number in enumerate(req.to_numbers):
                ok = client.send_message(number, req.message)
                if ok:
                    sent.append(number)
                else:
                    failed.append(number)

                if i < len(req.to_numbers) - 1:
                    time.sleep(self._delay_between_sends)

            # Compute final status
            if sent and not failed:
                status = WhatsAppBroadcastStatus.SUCCESS
            elif sent and failed:
                status = WhatsAppBroadcastStatus.PARTIAL
            else:
                status = WhatsAppBroadcastStatus.FAILED

            return WhatsAppBroadcastResult(
                request_id=req.request_id,
                sent=sent,
                failed=failed,
                status=status,
            )

        except Exception as exc:  # noqa: BLE001
            return WhatsAppBroadcastResult(
                request_id=req.request_id,
                status=WhatsAppBroadcastStatus.FAILED,
                error=str(exc),
            )
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _make_client(self):
        from golden_tier_external_world.watchers.whatsapp.models import WhatsAppConfig
        from golden_tier_external_world.watchers.whatsapp.client import PlaywrightWhatsAppClient

        config = WhatsAppConfig(phone_number="self", vault_root=self._vault_root)
        return PlaywrightWhatsAppClient(config, session_dir=self._session_dir)
