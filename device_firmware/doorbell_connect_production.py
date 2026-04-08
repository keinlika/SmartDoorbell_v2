#!/usr/bin/env python3
"""
Production entrypoint for the tuned hot-swap firmware.

This keeps a separate executable name for deployment while sharing the same
implementation and .env-driven camera tuning as doorbell_connect.py.
"""

import asyncio

import doorbell_connect as firmware


if __name__ == "__main__":
    try:
        asyncio.run(firmware.main())
    except KeyboardInterrupt:
        pass
    finally:
        firmware.GPIO.cleanup()
        with firmware.cap_lock:
            try:
                if firmware.cap is not None:
                    firmware.cap.release()
            except Exception:
                pass
