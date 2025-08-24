from app import app

# Vercel will call this 'app' WSGI object
if __name__ == "__main__":
    app.run()
