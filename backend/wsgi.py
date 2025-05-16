# Import app with a try-except block to handle both package and direct imports
try:
    # When imported as a module
    from .app import create_app
except ImportError:
    # When run directly
    from app import create_app

app, socketio = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
