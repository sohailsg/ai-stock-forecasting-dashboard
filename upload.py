"""
upload.py — uploads the dashboard and data files to a server via SFTP

Reads credentials from the .env file so passwords are never hard-coded.

Run on its own:  python upload.py
Or via:          python main.py  (which runs analyze first, then this)
"""

import os
import pathlib

import paramiko
from dotenv import load_dotenv

# Enforce that .env exists and override any shell-level env vars with its values.
_env_path = pathlib.Path(__file__).parent / ".env"
if not _env_path.exists():
    raise FileNotFoundError(
        f".env file not found at {_env_path}\n"
        "Copy .env.example to .env and fill in your SFTP credentials."
    )
load_dotenv(_env_path, override=True)


def get_config() -> dict:
    """Read SFTP settings from environment variables.

    Raises a clear error if any required variable is missing,
    so students know exactly what to add to their .env file.
    """
    required_keys = ["SFTP_HOST", "SFTP_USER", "SFTP_PASS", "SFTP_REMOTE_DIR"]
    config = {key: os.environ.get(key) for key in required_keys}

    missing = [key for key, value in config.items() if not value]
    if missing:
        raise EnvironmentError(
            f"Missing required variables in .env: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your SFTP credentials."
        )

    # SFTP_PORT is optional — defaults to 22 (the standard SFTP port)
    config["SFTP_PORT"] = int(os.environ.get("SFTP_PORT", 22))

    return config


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    """Create remote_dir on the server if it does not already exist."""
    try:
        sftp.stat(remote_dir)  # raises FileNotFoundError if missing
    except FileNotFoundError:
        sftp.mkdir(remote_dir)
        print(f"  Created remote directory: {remote_dir}")


def upload_directory(sftp: paramiko.SFTPClient, local_dir: pathlib.Path, remote_dir: str) -> None:
    """Upload every file in local_dir to remote_dir on the remote server.

    Notes:
    - sftp.put(local_path, remote_path) transfers the file in one call.
    - Hidden files (starting with ".") are skipped.
    """
    ensure_remote_dir(sftp, remote_dir)

    for local_file in sorted(local_dir.iterdir()):
        if not local_file.is_file():
            continue  # skip subdirectories
        if local_file.name.startswith("."):
            continue  # skip hidden files like .gitkeep

        remote_path = f"{remote_dir}/{local_file.name}"
        sftp.put(str(local_file), remote_path)
        print(f"  Uploaded: {local_file.name}  →  {remote_path}")


def main():
    config = get_config()

    print(f"Connecting to {config['SFTP_HOST']} ...")

    # SSHClient manages the underlying SSH connection.
    # AutoAddPolicy accepts the host key automatically — fine for a classroom
    # setting; in production you would verify the host key explicitly.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        config["SFTP_HOST"],
        port=config["SFTP_PORT"],
        username=config["SFTP_USER"],
        password=config["SFTP_PASS"],
        banner_timeout=60,  # seconds to wait for the SSH banner — NS shared hosting can be slow
    )
    print("Connected.\n")

    # open_sftp() opens an SFTP session over the SSH connection
    sftp = ssh.open_sftp()

    remote_dir = config["SFTP_REMOTE_DIR"]

    # Upload the JSON data files
    print("Uploading data files (output/)...")
    upload_directory(sftp, pathlib.Path("output"), f"{remote_dir}/output")

    # Upload the static dashboard (HTML, CSS, JS)
    print("\nUploading dashboard files (dashboard/)...")
    upload_directory(sftp, pathlib.Path("dashboard"), remote_dir)

    sftp.close()
    ssh.close()

    print("\nUpload complete. Visit your site to verify the dashboard is live.")


if __name__ == "__main__":
    main()
