from flask import Blueprint, Response, current_app, jsonify, request

api = Blueprint("api", __name__, url_prefix="/api")


def engine():
    return current_app.extensions["smartcross"]


def body():
    value = request.get_json()
    if not isinstance(value, dict):
        raise ValueError("Envie um objeto JSON.")
    return value


@api.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400


@api.errorhandler(RuntimeError)
def conflict(error):
    return jsonify(error=str(error)), 409


@api.get("/state")
def state():
    return jsonify(engine().snapshot())


@api.post("/source")
def source():
    if request.mimetype == "multipart/form-data":
        if set(request.form) - {"mode", "camera"} or set(request.files) - {"video"}:
            raise ValueError("Campos de fonte inválidos.")
        mode = request.form.get("mode")
        camera = int(request.form.get("camera", "0"))
        engine().select(mode, camera, request.files.get("video"))
    else:
        fields = body()
        if set(fields) - {"mode", "camera"}:
            raise ValueError("Campos de fonte inválidos.")
        engine().select(fields.get("mode"), fields.get("camera", 0))
    return state()


@api.post("/start")
def start():
    engine().start()
    return state()


@api.post("/stop")
def stop():
    engine().stop()
    return state()


@api.patch("/settings")
def settings():
    return jsonify(engine().configure(body()))


@api.put("/roi")
def roi():
    return jsonify(engine().configure({"roi": body()}))


@api.post("/simulation")
def simulation():
    engine().simulate(body().get("count"))
    return state()


@api.get("/events")
def events():
    return jsonify(engine().events.recent())


@api.get("/stats")
def stats():
    return jsonify(engine().events.stats())


@api.get("/stream")
def stream():
    session = engine().snapshot()
    if not session["running"] or session["source"] == "simulation":
        return "", 204
    return Response(engine().stream(session["run_id"]),
                    mimetype="multipart/x-mixed-replace; boundary=frame")
