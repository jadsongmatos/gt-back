import json
from celery.result import AsyncResult
from celery_app import celery
from .tasks import enqueue_file_processing

def handle(event, context):
    path   = '/' + event.path.strip('/')
    method = event.method.upper()

    # POST /process → só dispara a chain e retorna o task_id
    if path == '/process' and method == 'POST':
        payload = json.loads(event.body or '{}')
        file_path = payload.get('file_path')
        if not file_path:
            return {"statusCode": 400,
                    "body": {"error": "file_path é obrigatório"}}

        task_id, task_uuid = enqueue_file_processing(file_path)
        print("enqueue_file_processing",task_id)
        return {"statusCode": 202,
                "body": {"task_id": task_uuid, "status": "PENDING"}}

    if path == '/process' and method == 'GET':
        params  = event.query or {}
        task_id = params.get('task_id')
        if not task_id:
            return {"statusCode": 400,
                    "body": {"error": "task_id é obrigatório"}}

        result = AsyncResult(task_id, app=celery)
        return {
            "statusCode": 200,
            "body": {
                "task_id": task_id,
                "status": result.status,
                "result": str(result.result) if result.ready() else None,
                "traceback": str(result.traceback) if result.failed() else None
            }
        }

    return {"statusCode": 404, "body": {"error": "rota não encontrada"}}
