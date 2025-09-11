import threading, time

lock = threading.RLock()


# def task():
#     with lock:
#         print('Outer lock acquired')
#         with lock:
#             print('Inner lock acquired')

# threading.Thread(target=task).start()

# def factorial(n):
#     if n == 0:
#         return 1
#     with lock:
#         return n * factorial(n - 1)
#
# threading.Thread(target = factorial, args = (5, )).start()

# sem = threading.Semaphore(2)
#
# def worker(i):
#     with sem:
#         print(f'thread {i} entering')
#         time.sleep(2)
#         print(f'thread {i} exiting')
#
# for i in range(5):
#     threading.Thread(target=worker, args=(i, )).start()

event = threading.Event()

def background():
    while True:
        print('background thread running')
        time.sleep(1)

t = threading.Thread(target=background, daemon=True)
t.start()

time.sleep(3)
print('main program exiting')