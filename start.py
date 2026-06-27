import subprocess
import sys
import os


def main() -> None:
    print("Starting DispatchIQ...")
    print("WhatsApp service: http://localhost:3001")
    print("Web app: http://localhost:5000")
    print("Press Ctrl+C to stop both services.\n")

    wa = subprocess.Popen(
        ['node', 'index.js'],
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wa-sender'),
    )

    flask = subprocess.Popen([sys.executable, 'run.py'])

    try:
        flask.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        wa.terminate()
        flask.terminate()
        try:
            wa.wait(timeout=5)
        except subprocess.TimeoutExpired:
            wa.kill()
        try:
            flask.wait(timeout=5)
        except subprocess.TimeoutExpired:
            flask.kill()


if __name__ == '__main__':
    main()
