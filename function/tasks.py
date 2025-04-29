from celery import chain
from celery_app import celery, get_session
from function.models import FileProcess

# Passos atômicos:
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def step_read_file(self, file_id):
    with get_session() as db:
        fp = db.get(FileProcess, file_id)
        fp.status = 'PROCESSING'; fp.current_step = 1; db.add(fp)
        # … leia e retorne conteúdo parcial …
        data = open(fp.file_path, 'r').read()
        return data

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def step_process_data(self, prev_data, file_id):
    with get_session() as db:
        fp = db.get(FileProcess, file_id)
        fp.current_step = 2; db.add(fp)
        # … processe …
        processed = prev_data.upper()  # exemplo
        return processed

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def step_finalize(self, prev_processed, file_id):
    with get_session() as db:
        fp = db.get(FileProcess, file_id)
        fp.current_step = 3
        fp.result = {'final': prev_processed}
        fp.status = 'SUCCESS'; db.add(fp)
    return fp.result

def enqueue_file_processing(file_path):
    """Cria registro e dispara chain de processamento."""
    with get_session() as db:
        fp = FileProcess(file_path=file_path)
        db.add(fp); db.flush()
        file_id = fp.id
    # encadeia as subtarefas; cada uma é ACK só ao terminar
    result = chain(
        step_read_file.s(file_id),
        step_process_data.s(file_id),
        step_finalize.s(file_id)
    ).apply_async()
    return file_id, result.id  # devolve id do DB e id do Celery
