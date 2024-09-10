#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    'QueueEmpty',
    'SimpleQueue',
)

from collections import deque

from .locks import Semaphore
from .lowlevel import MISSING


class QueueEmpty(Exception):
    pass


class SimpleQueue:
    __slots__ = (
        '__lock',
        '__queue'
    )
    
    @staticmethod
    def __new__(cls, /, items=MISSING):
        self = super(SimpleQueue, cls).__new__(cls)
        
        self.__lock = Semaphore(0)
        
        if items is MISSING:
            self.__queue = deque()
        else:
            self.__queue = queue = deque(items)
            
            if queue:
                self.__lock.release(len(queue))
        
        return self
    
    def __getnewargs__(self, /):
        return (list(self.__queue),)
    
    def __repr__(self, /):
        return f"SimpleQueue({list(self.__queue)!r})"
    
    def __bool__(self, /):
        return bool(self.__queue)
    
    def __len__(self, /):
        return len(self.__queue)
    
    def put(self, /, item):
        self.__queue.append(item)
        self.__lock.release()
    
    async def aget(self, /, *, blocking=True):
        success = await self.__lock.async_acquire(blocking=blocking)
        
        if not success:
            raise QueueEmpty
        
        return self.__queue.popleft()
    
    def get(self, /, *, blocking=True, timeout=None):
        success = self.__lock.green_acquire(blocking=blocking, timeout=timeout)
        
        if not success:
            raise QueueEmpty
        
        return self.__queue.popleft()
    
    @property
    def waiting(self, /):
        return self.__lock.waiting
