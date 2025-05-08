from .image_data_pb2 import ImageData

import logging
import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from celery import Task, chain
from celery.signals import worker_process_init

from ultralytics import YOLO
from ultralytics.utils import ThreadingLocked

from celery_app import celery, get_session
from function.models import FileProcess, StatusEnum
from functools import lru_cache

logger = logging.getLogger(__name__)
if not logger.handlers:
    fh = logging.FileHandler("celery_yolo.log")
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
logger.setLevel(logging.INFO)

MODEL_PATH = "./function/weights/best.pt"

class BinaryPayload:
    def __init__(self, data: bytes):
        self.data = data

    def __repr__(self):
        return "<binary data>"

    def get(self) -> bytes:
        return self.data


@lru_cache(maxsize=1)
def get_model() -> YOLO:
    abs_path = Path(MODEL_PATH).resolve()
    logger.info("Loading YOLO model from %s", abs_path)
    if not abs_path.exists():
        logger.error("Model file does not exist at: %s", abs_path)
    return YOLO(str(abs_path))

@worker_process_init.connect
def preload_model(**kwargs):
    # Ensures one model load per worker process
    _ = get_model()

# Even if this task ever uses threads internally, only one thread at a time
safe_predict = ThreadingLocked()(get_model().predict)

class BaseRetryTask(Task):
    autoretry_for = (Exception,)
    max_retries = 2
    default_retry_delay = 1
    retry_backoff = True
    retry_jitter = True
    acks_late = True
    reject_on_worker_lost = True

    def filter_args(self, args, kwargs):
        if self.name == "function.tasks.step_process_data":
            # Substitui image_proto por marcador para evitar log do conteúdo binário
            args = ("<binary>",) + tuple(args[1:])
        return args, kwargs

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        args, kwargs = self.filter_args(args, kwargs)
        logger.warning("[RETRY] %s args=%r exc=%s", self.name, args, exc)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        args, kwargs = self.filter_args(args, kwargs)
        logger.error("[FAIL] %s args=%r exc=%s", self.name, args, exc)

    def on_success(self, retval, task_id, args, kwargs):
        args, kwargs = self.filter_args(args, kwargs)
        logger.info("[OK] %s args=%r", self.name, args)

@celery.task(bind=True, base=BaseRetryTask)
def step_read_file(self, file_id: int) -> bytes | None:
    with get_session() as db:
        fp: FileProcess = db.get(FileProcess, file_id)
        path = Path(fp.file_path)

        # Missing file retry
        if not path.is_file():
            msg = f"File not found: {path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        try:
            # Force load & validation
            with Image.open(path) as img:
                img.load()

            # Update status only after successful validation
            fp.status = StatusEnum.PROCESSING
            fp.current_step = 1
            db.add(fp)
            db.commit()

            # Serialize image to protobuf
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            proto = ImageData(content=buffer.getvalue(), format="JPEG")
            return proto.SerializeToString()

        except UnidentifiedImageError:
            # Bad image mark error, do NOT retry
            logger.error("Invalid image format: %s", path)
            fp.status = StatusEnum.FAILURE
            db.add(fp)
            db.commit()
            return None

        except Exception:
            # Unexpected let Celery retry
            logger.exception("Unexpected error loading image")
            raise

@celery.task(bind=True, base=BaseRetryTask)
def step_process_data(self, image_proto: bytes, file_id: int) -> dict:
    with get_session() as db:
        fp: FileProcess = db.get(FileProcess, file_id)

        # Decode protobuf PIL image
        try:
            proto = ImageData()
            proto.ParseFromString(image_proto)
            img = Image.open(io.BytesIO(proto.content))
        except Exception as e:
            logger.error("Failed to decode protobuf image: %s", e)
            fp.status = StatusEnum.ERROR
            db.add(fp)
            db.commit()
            raise

        # Thread-safe prediction
        try:
            results = safe_predict(source=img, conf=0.5)
        except Exception:
            logger.exception("YOLO inference error")
            raise

        # Persist results
        fp.current_step = 2
        fp.status = StatusEnum.SUCCESS
        fp.result = {"predict": results[0].to_json()} 
        db.add(fp)
        db.commit()

        return fp.result

def enqueue_file_processing(file_path: str) -> tuple[int, str]:
    with get_session() as db:
        fp = FileProcess(file_path=file_path)
        db.add(fp)
        db.flush()
        file_id = fp.id
        db.commit()

    # Chain the two steps
    res = chain(
        step_read_file.s(file_id),
        step_process_data.s(file_id),
    ).apply_async()

    return file_id, res.id
