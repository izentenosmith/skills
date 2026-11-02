"""Renders invoice PDFs and thumbnails from the queue table. Uses /dev/dri when present."""
import os
import time


def main():
    gpu = os.path.exists("/dev/dri/renderD128")
    while True:
        time.sleep(5)  # poll the queue (elided)


if __name__ == "__main__":
    main()
