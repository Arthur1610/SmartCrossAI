import logging
from threading import Condition, Event, Thread
from time import monotonic

from .config import Settings
from .lighting import Lighting, Phase
from .sources import Sources
from .vision import Vision

log = logging.getLogger(__name__)


class Engine:
    def __init__(self, events, cache):
        self.events = events
        self.vision = Vision(cache)
        self.sources = Sources()
        self.settings = Settings()
        self.lighting = Lighting()
        self.changed = Condition()
        self.cancel = Event()
        self.worker = None
        self.status = "Parado"
        self.error = None
        self.people = self.inside = self.simulated = 0
        self.fps = None
        self.jpeg = None
        self.sequence = 0
        self.run_id = 0

    def snapshot(self):
        with self.changed:
            start = self.lighting.active_since
            return {
                "source": self.sources.mode, "camera": self.sources.camera,
                "running": self.worker is not None, "status": self.status,
                "error": self.error, "people": self.people, "inside": self.inside,
                "fps": self.fps, "phase": self.lighting.phase, "leds": start is not None,
                "elapsed": round(monotonic() - start, 1) if start is not None else 0,
                "settings": self.settings.json(), "stream_ready": self.jpeg is not None,
                "run_id": self.run_id,
            }

    def select(self, mode, camera, file=None):
        with self.changed:
            if self.worker is not None:
                raise RuntimeError("Pare a análise antes de mudar de fonte.")
            self.sources.select(mode, camera, file)
            self.status, self.error = "Parado", None

    def configure(self, fields):
        with self.changed:
            self.settings = self.settings.update(fields)
            if self.lighting.phase == Phase.CONFIRMING:
                self.lighting = Lighting()
            return self.settings.json()

    def simulate(self, count):
        with self.changed:
            if self.sources.mode != "simulation" or self.worker is None or self.cancel.is_set():
                raise RuntimeError("Inicie o modo simulação.")
            if type(count) is not int or not 0 <= count <= 5:
                raise ValueError("Informe de 0 a 5 pessoas.")
            self.simulated = count

    def start(self):
        with self.changed:
            if self.worker is not None:
                raise RuntimeError("Já existe uma análise em execução.")
            self.cancel.clear()
            self.run_id += 1
            self.status, self.error = "Preparando fonte", None
            self.worker = Thread(target=self.run, name="smartcross-capture", daemon=True)
            self.worker.start()

    def stop(self, wait=0):
        with self.changed:
            worker = self.worker
            if worker is not None:
                self.status = "Interrompendo"
                self.cancel.set()
                self.changed.notify_all()
        if worker is not None and wait:
            worker.join(wait)

    def close(self):
        self.stop(wait=5)
        with self.changed:
            if self.worker is None:
                self.sources.close()

    def record(self, kind, count):
        try:
            self.events.add(kind, self.sources.mode, count)
        except Exception:
            log.exception("Falha ao registrar evento")
            self.error = "Falha ao gravar o histórico local."

    def publish(self, total, inside, settings, fps=None, jpeg=None):
        with self.changed:
            if self.cancel.is_set() or settings is not self.settings:
                return
            if inside != self.inside:
                self.record("entrada_roi" if inside > self.inside else "saida_roi", inside)
            self.people, self.inside, self.fps = total, inside, fps
            event = self.lighting.update(inside > 0, monotonic(), settings.confirmation, settings.hold)
            if event:
                self.record(event, inside)
            self.status = "Em análise"
            if jpeg is not None:
                self.jpeg = jpeg
                self.sequence += 1
                self.changed.notify_all()

    def run(self):
        status, error = "Parado", None
        capture = None
        mode = self.sources.mode
        try:
            if mode == "simulation":
                while not self.cancel.is_set():
                    with self.changed:
                        self.publish(self.simulated, self.simulated, self.settings)
                    self.cancel.wait(.05)
                return

            import cv2

            capture = self.sources.open(cv2)
            ok, frame = capture.read()
            if not ok:
                message = ("Webcam indisponível. Verifique o índice e as permissões do Windows."
                           if mode == "webcam" else "Não foi possível ler o MP4.")
                raise RuntimeError(message)
            with self.changed:
                if self.cancel.is_set():
                    return
                self.status = "Carregando YOLOv8n"
            try:
                self.vision.load()
            except Exception as exc:
                raise RuntimeError("Falha ao carregar o YOLOv8n. Confira a instalação e a conexão para baixar os pesos.") from exc
            video_fps = capture.get(cv2.CAP_PROP_FPS)
            period = 1 / video_fps if mode == "video" and 1 <= video_fps <= 240 else 0
            fps = None
            while not self.cancel.is_set():
                started = monotonic()
                with self.changed:
                    settings = self.settings
                try:
                    total, inside, jpeg = self.vision.analyze(cv2, frame, settings)
                except Exception as exc:
                    raise RuntimeError("Falha durante a análise. Consulte o terminal.") from exc
                sample = 1 / max(.001, monotonic() - started)
                fps = sample if fps is None else .2 * sample + .8 * fps
                self.publish(total, inside, settings, round(fps, 1), jpeg)
                if self.cancel.wait(max(0, period - (monotonic() - started))):
                    break
                ok, frame = capture.read()
                if not ok:
                    if mode == "webcam":
                        raise RuntimeError("A webcam parou de enviar imagens.")
                    status = "Fim do vídeo"
                    break
        except Exception as exc:
            if not self.cancel.is_set():
                log.exception("Falha na fonte %s", mode)
                status = "Falha"
                error = str(exc) if isinstance(exc, RuntimeError) else "Falha ao processar a fonte. Consulte o terminal."
        finally:
            try:
                if capture is not None:
                    capture.release()
            finally:
                with self.changed:
                    self.status, self.error = status, error
                    if self.inside:
                        self.record("saida_roi", 0)
                    if self.lighting.active_since is not None:
                        self.record("desativacao", 0)
                    self.lighting = Lighting()
                    self.people = self.inside = self.simulated = 0
                    self.jpeg = self.fps = None
                    self.worker = None
                    self.changed.notify_all()

    def stream(self, run_id):
        last = -1
        while True:
            with self.changed:
                self.changed.wait_for(lambda: self.worker is None or self.cancel.is_set()
                                      or self.run_id != run_id
                                      or (self.jpeg is not None and last != self.sequence))
                if self.worker is None or self.cancel.is_set() or self.run_id != run_id:
                    return
                jpeg, last = self.jpeg, self.sequence
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
