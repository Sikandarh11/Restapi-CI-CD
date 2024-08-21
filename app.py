from flask import render_template
from extensions import app
from blueprints.auth import auth_bp
from blueprints.post import posts_bp

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(posts_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)