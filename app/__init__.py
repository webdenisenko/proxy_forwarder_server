""" Run App script """
from decouple import config
from flask import Flask

from app.views import routes

# create app
app = Flask(__name__)

# registrate routes
app.register_blueprint(routes)

# runner
if __name__ == '__main__':
    PUBLIC_API_PORT = config('PUBLIC_API_PORT', default=8000, cast=int)
    DEBUG = config('DEBUG', default=True, cast=bool)

    app.run(port=PUBLIC_API_PORT, debug=DEBUG)