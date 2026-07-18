import argparse
import os
import shlex
import subprocess
import time

WAYLAND_SOCKET = "wayland-nested"
XWAYLAND_DISPLAY = "1"


def main():
    parser = argparse.ArgumentParser("KWin Start Nested")

    parser.add_argument(
        "command",
        help="Command to execute in the nested KWin session.",
        type=str,
        nargs="?",
    )

    args = parser.parse_args()

    cmd = [
        "kwin_wayland",
        "--xwayland",
        "--xwayland-display",
        f":{XWAYLAND_DISPLAY}",
        # "--xwayland-xauthority",
        # "/tmp/xauth_nested",
        "--width",
        "1280",
        "--height",
        "720",
        "--socket",
        WAYLAND_SOCKET,
        "--no-global-shortcuts",
        "--no-lockscreen",
    ]

    # Nesting options based on host session display variables
    if "WAYLAND_DISPLAY" in os.environ:
        cmd.extend(["--wayland-display", os.environ["WAYLAND_DISPLAY"]])
    else:
        raise RuntimeError(
            "WAYLAND_DISPLAY is not set in your environment, make sure KWin is running in Wayland mode"
        )

    proc: subprocess.Popen[bytes] | None = None

    try:
        proc = subprocess.Popen(
            cmd,
            preexec_fn=os.setsid,  # Run in a new process group for clean termination
        )

        print(
            "\n================================================================================\n"
        )
        print(
            "Nested KWin is running. To run an application inside this nested session use:"
        )
        print(
            f"  WAYLAND_DISPLAY={WAYLAND_SOCKET} DISPLAY=:{XWAYLAND_DISPLAY} <your-app>"
        )
        print(
            "\n================================================================================\n"
        )

        if args.command:
            time.sleep(1)
            env = os.environ.copy()
            env["WAYLAND_DISPLAY"] = WAYLAND_SOCKET
            env["DISPLAY"] = f":{XWAYLAND_DISPLAY}"
            subprocess.Popen(shlex.split(args.command), env=env)

        proc.wait()
    except KeyboardInterrupt:
        print("\nTerminating nested KWin...")
    finally:
        if proc:
            proc.terminate()


if __name__ == "__main__":
    main()
