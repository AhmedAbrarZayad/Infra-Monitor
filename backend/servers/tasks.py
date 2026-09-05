from celery import shared_task

from servers.services.lifecycle import evaluate_all_services


@shared_task(name="servers.evaluate_service_lifecycle")
def evaluate_service_lifecycle():
    return evaluate_all_services()
