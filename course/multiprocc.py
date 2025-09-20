import multiprocessing as mp
import os
import time


def worker(name):
    time.sleep(10)
    print(f'Worker {name} running in process id: {os.getpid()}')
    time.sleep(10)
    print(f'Worker {name} exiting')

if __name__ == '__main__':
    p1 = mp.Process(target=worker, args=('A',))
    p2 = mp.Process(target=worker, args=('B',))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    print("Both processes finished")