import os


class Vision:
    def __init__(self, cache):
        self.cache = cache
        self.model = None

    def load(self):
        if self.model is None:
            self.cache.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("YOLO_CONFIG_DIR", str(self.cache))
            from ultralytics import YOLO, settings

            settings.update({"sync": False, "weights_dir": str(self.cache)})
            self.model = YOLO(str(self.cache / "yolov8n.pt"))

    def analyze(self, cv, frame, settings):
        height, width = frame.shape[:2]
        if width > 960:
            frame = cv.resize(frame, (960, max(1, round(height * 960 / width))))
            height, width = frame.shape[:2]
        result = self.model.predict(frame, classes=[0], conf=settings.confidence,
                                    device="cpu", imgsz=640, verbose=False)[0]
        roi = settings.roi
        cv.rectangle(frame, (round(roi.x * width), round(roi.y * height)),
                     (round((roi.x + roi.width) * width), round((roi.y + roi.height) * height)),
                     (240, 200, 42), 2)
        inside = 0
        for box, confidence in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
            in_roi = roi.contains(box, width, height)
            inside += in_roi
            left, top, right, bottom = map(int, box)
            color = (130, 240, 68) if in_roi else (235, 170, 70)
            cv.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv.circle(frame, ((left + right) // 2, min(bottom, height - 1)), 4, color, -1)
            label = f"Pessoa {confidence:.0%} | {'na zona' if in_roi else 'fora'}"
            cv.putText(frame, label, (left, max(16, top - 5)), cv.FONT_HERSHEY_SIMPLEX,
                       .48, color, 1, cv.LINE_AA)
        success, jpg = cv.imencode(".jpg", frame, [cv.IMWRITE_JPEG_QUALITY, 82])
        if not success:
            raise RuntimeError("Não foi possível codificar a imagem.")
        return len(result.boxes), inside, jpg.tobytes()
