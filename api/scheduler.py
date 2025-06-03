from app.scheduler import run


def handler(request):
    run()
    return {"status": "ok"}
