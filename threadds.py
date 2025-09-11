import random
import threading
import time

# global_var = []
#
# def worker(name):
#     print(f'thread {name} starting')
#     sleep_time = random.randint(1, 5)
#     time.sleep(sleep_time)
#     global_var.append(sleep_time)
#     print(f'thread {name} finished')
#
#
# t1 = threading.Thread(target=worker, args = ('A', ))
# t2 = threading.Thread(target=worker, args = ('B', ))
# t1.start()
# t2.start()
# global_var.append(random.randint(1, 5))
# t1.join()
# t2.join()
# print('both treads finished')
# print(global_var)

# counter = 0
# lock = threading.Lock()
#
# def increment():
#     global counter
#     for _ in range(100000):
#         with lock:
#             counter += 1
#
# threads = [threading.Thread(target=increment) for _ in range(5)]
# for t in threads:
#     t.start()
# for t in threads:
#     t.join()
# print('final counter: ', counter)

counter = 0
lock1 = threading.Lock()
lock2 = threading.Lock()

def increment():
    global counter
    for _ in range(10000):
        with lock1:
            with lock2:
                counter += 1

        with lock2:
            with lock1:
                counter -= 1


threads = [threading.Thread(target=increment) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print('final counter: ', counter)

