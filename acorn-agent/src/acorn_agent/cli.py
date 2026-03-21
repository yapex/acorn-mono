"""
CLI entry point for acorn-agent
"""

import signal
import sys

from .server import AcornServer


def main():
    server = AcornServer()
    
    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
