from waitress import serve
from config.wsgi import application
from django.conf import settings
from whitenoise import WhiteNoise

if __name__ == "__main__":
    # Wrap da aplicação com WhiteNoise (serve arquivos estáticos)
    app = WhiteNoise(application, root=str(settings.STATIC_ROOT))
    app.add_files(str(settings.STATIC_ROOT), prefix=settings.STATIC_URL)
    app.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL)

    serve(app, host="0.0.0.0", port=5010)
