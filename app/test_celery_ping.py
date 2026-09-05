from app.tasks import ping

result = ping.delay()
print("Task submitted, id:", result.id)
print("Result:", result.get(timeout=10))