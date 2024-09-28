#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = ("CapacityLimiter",)

from aiologic.lowlevel import (
    current_async_task_ident,
    current_green_task_ident,
)

from .semaphore import Semaphore


class CapacityLimiter:
    __slots__ = (
        "__weakref__",
        "__semaphore",
        "__waiters",
        "borrowers",
    )

    @staticmethod
    def __new__(cls, /, total_tokens):
        self = super(CapacityLimiter, cls).__new__(cls)

        if total_tokens < 1:
            raise ValueError("total_tokens must be >= 1")

        self.__semaphore = Semaphore(total_tokens)

        self.__waiters = {}
        self.borrowers = set()

        return self

    def __getnewargs__(self, /):
        return (self.__semaphore.initial_value,)

    def __repr__(self, /):
        return f"CapacityLimiter({self.__semaphore.initial_value!r})"

    async def __aenter__(self, /):
        await self.async_acquire()

        return self

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        self.async_release()

    def __enter__(self, /):
        self.green_acquire()

        return self

    def __exit__(self, /, exc_type, exc_value, traceback):
        self.green_release()

    async def async_acquire_on_behalf_of(self, /, borrower, *, blocking=True):
        marker = object()

        if self.__waiters.setdefault(borrower, marker) is not marker:
            if borrower not in self.borrowers:
                raise RuntimeError(
                    "this borrower is already waiting for"
                    " any of this CapacityLimiter's tokens",
                )
            else:
                raise RuntimeError(
                    "this borrower is already holding"
                    " one of this CapacityLimiter's tokens",
                )

        success = False

        try:
            success = await self.__semaphore.async_acquire(blocking=blocking)
        finally:
            if success:
                self.borrowers.add(borrower)
            else:
                del self.__waiters[borrower]

        return success

    async def async_acquire(self, /, *, blocking=True):
        return await self.async_acquire_on_behalf_of(
            current_async_task_ident(),
            blocking=blocking,
        )

    def green_acquire_on_behalf_of(
        self,
        /,
        borrower,
        *,
        blocking=True,
        timeout=None,
    ):
        marker = object()

        if self.__waiters.setdefault(borrower, marker) is not marker:
            if borrower not in self.borrowers:
                raise RuntimeError(
                    "this borrower is already waiting for"
                    " any of this CapacityLimiter's tokens",
                )
            else:
                raise RuntimeError(
                    "this borrower is already holding"
                    " one of this CapacityLimiter's tokens",
                )

        success = False

        try:
            success = self.__semaphore.green_acquire(
                blocking=blocking,
                timeout=timeout,
            )
        finally:
            if success:
                self.borrowers.add(borrower)
            else:
                del self.__waiters[borrower]

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        return self.green_acquire_on_behalf_of(
            current_green_task_ident(),
            blocking=blocking,
            timeout=timeout,
        )

    def async_release_on_behalf_of(self, /, borrower):
        try:
            self.borrowers.remove(borrower)
        except KeyError:
            raise RuntimeError(
                "this borrower is not holding"
                " any of this CapacityLimiter's tokens",
            ) from None
        else:
            del self.__waiters[borrower]

        self.__semaphore.async_release()

    def async_release(self, /):
        self.async_release_on_behalf_of(current_async_task_ident())

    def green_release_on_behalf_of(self, /, borrower):
        try:
            self.borrowers.remove(borrower)
        except KeyError:
            raise RuntimeError(
                "this borrower is not holding"
                " any of this CapacityLimiter's tokens",
            ) from None
        else:
            del self.__waiters[borrower]

        self.__semaphore.green_release()

    def green_release(self, /):
        self.green_release_on_behalf_of(current_green_task_ident())

    @property
    def waiting(self, /):
        return self.__semaphore.waiting

    @property
    def available_tokens(self, /):
        return self.__semaphore.value

    @property
    def borrowed_tokens(self, /):
        return self.__semaphore.initial_value - self.__semaphore.value

    @property
    def total_tokens(self, /):
        return self.__semaphore.initial_value
