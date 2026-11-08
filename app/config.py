"""Runtime configuration. Secrets live here on the HOST only.

The Vultr inference key is read from the host environment and is never
passed into a sandbox container.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    vultr_inference_api_key: str = ""
    vultr_inference_base_url: str = "https://api.vultrinference.com/v1"
    planner_model: str = "mimo-v2.6-pro"  # live model list verified 2026-11-03 (api.vultrinference.com/docs/models)
    planner_max_retries: int = 2  # error-feedback replans per run, each ledger-logged

    sandbox_image: str = "proofcell-sandbox:latest"
    sandbox_mem_limit: str = "512m"
    sandbox_nano_cpus: int = 1_000_000_000  # 1 CPU
    sandbox_pids_limit: int = 256
    sandbox_step_timeout_s: int = 60
    sandbox_run_timeout_s: int = 600

    data_dir: str = "runs"  # ledgers + artifacts, on the host


settings = Settings()
