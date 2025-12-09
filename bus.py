# bus.py
from __future__ import annotations
from enum import IntEnum, IntFlag
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable, TYPE_CHECKING

import weakref
from collections import deque

if TYPE_CHECKING:
    from .elements import UIElement

# Globals

BROADCAST = -1

class Response(IntEnum):
    # STATES
    R_OK = 0
    R_ERROR = 1
    R_DISPOSED = 2

    # COMMANDS
    R_RESET = 10
    R_TERMINATE = 11
    
    # ASSETS
    R_CLEAR = 20    # assets reset
    R_FONT = 21     # font asset available
    R_VIS = 22      # visual assets available
    
    # METADATA
    R_GET = 40
    R_DATA = 41 

@dataclass(frozen=True)
class Packet:
    receiver: int
    sender: int
    rs: Response = Response.R_OK
    data: Any = None



class AddressBus:
    __slots__ = (
        "_queue",
        "_elements",
        "_handler_cache",
        "_next_addr",
        "_cleanup_count",
        "_processed",
    )

    def __init__(self, cleanup_threshold: int = 1000) -> None:
        self._next_addr     : int = 1
        self._processed: int = 0
        self._cleanup_count : int = cleanup_threshold
        self._queue         : deque[Packet] = deque()
        self._elements      : Dict[int, weakref.ReferenceType['UIElement']] = {}
        self._handler_cache : Dict[int, Optional[Callable]] = {}

    def register(self, e: 'UIElement') -> int:
        if not hasattr(e, "address") or e.address < 0:
            e.address = self._next_addr
            self._next_addr += 1

        addr = e.address

        # weakref cleanup
        def cleanup(ref: weakref.ReferenceType) -> None:
            self._elements.pop(addr, None)
            self._handler_cache.pop(addr, None)

        # store weak reference
        self._elements[addr] = weakref.ref(e, cleanup)

        name = getattr(e, "name", repr(e))
        print(f"[register] element({name}) at {addr}")

        # cache handler if it exists
        handler = getattr(e, "handle_message", None)
        self._handler_cache[addr] = handler if callable(handler) else None
        return addr

    def unregister(self, e: 'UIElement') -> None:
        addr = getattr(e, "address", None)
        if addr is not None:
            name = getattr(e, "name", repr(e))
            print(f"[unregister] element({name}) at {addr}")
            self._elements.pop(addr, None)
            self._handler_cache.pop(addr, None)

    def post(self, msg: Packet) -> bool:
        self._queue.append(msg)
        self._write_debug(msg)
        return True

    def pump(self) -> int:
        if not self._queue:
            return 0

        processed = 0
        messages = list(self._queue)
        self._queue.clear()

        for msg in messages:
            if msg.receiver == BROADCAST:
                # Iterate over a copy of items in case a handler modifies the cache (e.g., destroy)
                for addr, handler in list(self._handler_cache.items()):
                    if handler is not None:
                        self._call_handler(handler, msg, addr)
                        processed += 1
            else: # unicast
                handler = self._handler_cache.get(msg.receiver)
                if handler is not None:
                    self._call_handler(handler, msg, msg.receiver)
                    processed += 1

        # periodic cleanup
        self._processed += processed
        if self._processed >= self._cleanup_count:
            self._cleanup()
            self._processed = 0
        return processed

    def _write_debug(self, msg: Packet) -> None:
        if msg.receiver == BROADCAST:
            print(f"[BROADCAST] from: {msg.sender}; [rs={msg.rs.name}]")
        else:
            print(f"[MESSAGE] from: {msg.sender} to: {msg.receiver}; [rs={msg.rs.name}]") 
            
    def _call_handler(self, handler: Callable, msg: Packet, addr: int) -> None:
        try:
            handler(msg)
        except Exception as exc:
            # Retrieve the element name for better error reporting
            cref = self._elements.get(addr)
            comp = cref() if cref else None
            comp_name = getattr(comp, "name", f"Element@{addr}")
            
            # Print a more detailed error message including the message type
            print(f"Error: handler exception in {comp_name} for message {msg.rs.name}: {exc}")
            # Optionally, log the full traceback for debugging
            # import traceback
            # traceback.print_exc()

    def _cleanup(self) -> None:
        for addr, ref in list(self._elements.items()):
            if ref() is None:
                self._elements.pop(addr, None)
                self._handler_cache.pop(addr, None)

    # QoL Functions

    def clear(self) -> None:
        """Clear all queued messages."""
        self._queue.clear()