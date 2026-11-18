import logging

from smartcross import create_app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    app = create_app()
    print("SmartCross AI: http://127.0.0.1:5000")
    try:
        app.run(host="127.0.0.1", port=5000, threaded=True, use_reloader=False)
    finally:
        app.extensions["smartcross"].close()
