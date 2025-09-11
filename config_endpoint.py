import multiprocessing as mp
import os
import time
import subprocess



# def add_routes(dest_ip, next_hop):
#     route = subprocess.run(['ip', 'route', 'add', f'{dest_ip}/24', 'via', f'{next_hop}'])
# if __name__ == '__main__':
#
#     subprocess.run(['ip', 'addr', 'add', '192.168.100.100/24', 'dev', 'ens4'])
#     processes = []
#
#
#     for i in range(1,5):
#         p = mp.Process(target=add_routes, args = (f'192.168.10{i}.0', f'192.168.100.{i}'))
#         processes.append(p)
#
#     print("Starting to set routes")
#     for proc in processes:
#         proc.start()
#
#     print("Setting routes")
#     for proc in processes:
#         proc.join()
#
#     print("All processes finished")


from multiprocessing import Process, Pool, Queue

# def square(x):
#     print(f'{os.getpid()}: square(x={x})')
#     time.sleep(5)
#     return x * x
#
# if __name__ == '__main__':
#     start = time.time()
#     with Pool(5) as pool:
#         results = pool.map(square, [1,2,3,4,5])
#         print(results)
#     end = time.time()
#     print(end - start)

def producer(q):
    for i in range(5):
        time.sleep(1)
        q.put(i)

def consumer(q):
    while not q.empty():
        item = q.get()
        print("Consuming: ", item)
        time.sleep(0.9)
        print("Consumed: ", item)
    print("Consumer finished: ", os.getpid())
if __name__ == "__main__":

    q = Queue()
    p1 = Process(target=producer, args=(q,))
    p2 = Process(target=consumer, args=(q,))
    p3 = Process(target=consumer, args=(q,))
    p1.start()
    time.sleep(3)
    p2.start()
    p3.start()
    p1.join()
    p2.join()
    p3.join()

