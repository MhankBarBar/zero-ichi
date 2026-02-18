import os
import sys
from pathlib import Path

from core.logger import log_bullet, log_error, log_step, log_success, log_warning
from core.runtime_config import runtime_config


def validate_environment():
    """
    Validate environment variables and runtime configuration.
    Prints warnings/errors and exits if critical settings are missing.
    """
    log_step("Validating environment...")

    root_dir = Path(__file__).parent.parent
    data_dir = root_dir / "data"
    logs_dir = root_dir / "logs"

    for d in [data_dir, logs_dir]:
        if not d.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
                log_success(f"Created directory: {d.relative_to(root_dir)}")
            except Exception as e:
                log_error(f"Failed to create {d}: {e}")
                sys.exit(1)

        test_file = d / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            log_error(f"Directory {d} is not writable: {e}")
            sys.exit(1)

    login_method = runtime_config.login_method
    if login_method == "pair_code":
        phone = runtime_config.phone_number
        if not phone:
            log_error("PHONE_NUMBER is required for 'pair_code' login method!")
            log_bullet("Please update config.json.")
            sys.exit(1)
        if not phone.isdigit():
            log_warning(
                f"PHONE_NUMBER '{phone}' seems invalid (should be digits only with country code)."
            )

    user = os.getenv("DASHBOARD_USERNAME")
    password = os.getenv("DASHBOARD_PASSWORD")

    if not user or not password:
        log_warning(
            "DASHBOARD_USERNAME or DASHBOARD_PASSWORD not set. Using defaults (admin:admin)."
        )
        log_bullet("This is INSECURE for production deployments!")
    else:
        log_success("Dashboard credentials configured via environment variables.")

    ai_config = runtime_config.get("agentic_ai", {})
    if ai_config.get("enabled"):
        provider = ai_config.get("provider", "openai")
        api_key = (
            ai_config.get("AI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )

        if not api_key:
            log_warning(f"AI is enabled but no API key found for provider '{provider}'.")
            log_bullet("AI features may fail to initialize.")
        else:
            log_success(f"AI configured with provider: {provider}")

    log_success("Environment validation complete.")
