from pathlib import Path
from tempfile import TemporaryDirectory


class Sources:
    def __init__(self):
        self.mode = "simulation"
        self.camera = 0
        self.upload = None

    @property
    def path(self):
        return str(Path(self.upload.name) / "input.mp4")

    def select(self, mode, camera, file=None):
        if mode not in ("simulation", "webcam", "video"):
            raise ValueError("Selecione uma fonte válida.")
        if type(camera) is not int or not 0 <= camera <= 9:
            raise ValueError("Selecione uma câmera entre 0 e 9.")
        if mode == "video":
            if file is None and self.upload is None:
                raise ValueError("Selecione um arquivo MP4.")
            if file is not None:
                if not file.filename or not file.filename.lower().endswith(".mp4"):
                    raise ValueError("Selecione um arquivo MP4.")
                header = file.stream.read(12)
                if len(header) != 12 or header[4:8] != b"ftyp":
                    raise ValueError("O arquivo não tem cabeçalho MP4 compatível.")
                upload = TemporaryDirectory(prefix="smartcross-")
                try:
                    with (Path(upload.name) / "input.mp4").open("wb") as target:
                        target.write(header)
                        file.save(target)
                except BaseException:
                    upload.cleanup()
                    raise
                self.close()
                self.upload = upload
        else:
            self.close()
        self.mode, self.camera = mode, camera

    def open(self, cv):
        return cv.VideoCapture(self.camera if self.mode == "webcam" else self.path)

    def close(self):
        if self.upload is not None:
            self.upload.cleanup()
            self.upload = None
