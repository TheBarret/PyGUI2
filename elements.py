# elements.py

from __future__ import annotations
import pygame
import time

from typing import Dict, Callable, Optional, Tuple, List, Any
from bus import Packet, Response, BROADCAST


# ############################################
#
# Element Chassis
# 

class UIChassis:
    __slots__ = ('name', 'color', 'border', 'rect', 'parent', 'children', 
                 'address', 'active', 'visible', 'redraw', 'disposed', 
                 'passthrough', 'events', 'cache', 'cache_r', 'depth', 
                 'depth_max', 'store')
    def __init__(self, x: int = 0, y: int = 0, width: int = 1, height: int = 1):
        self.name           = 'UIElement'
        self.color          = (0, 0, 0)
        self.border         = (155, 55, 55)
        
        # geometry
        self.rect           = pygame.Rect(x, y, width, height)
        # structures
        self.parent         : Optional['UIChassis'] = None
        self.children       : List['UIChassis'] = []
        # states
        self.address        = -1
        self.active         = False
        self.visible        = True
        self.redraw         = True
        self.disposed       = False
        self.passthrough    = False
        # event handlers
        self.events         : Dict[str, List[Callable]] = {event: [] for event in 
                             ["click", "hover", "focus", "blur", "keypress"]}
        # cache
        self.cache          : Optional['UIElement'] = None
        self.cache_r        : Optional[pygame.Rect] = None
        
        # hierachy
        self.depth          : int = 0
        self.depth_max      : int = 255
        
        # internal db store
        self.store          = {}
        
    # Core routines
    
    def update(self, dt: float) -> None:
        if self.disposed:
            return
        for child in self.children:
            child.update(dt)
    
    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible or self.disposed:
            return
        abs_rect = self.get_absolute_rect()

        if self.has_local('frame.active'):
            pygame.draw.rect(surface, self.read_local('frame.active'), abs_rect)
            pygame.draw.rect(surface, self.read_local('frame.border'), abs_rect, 1)
        
        if self.has_local('font') and self.has_local('font.color'):
            _font = self.read_local('font')
            text_surf = _font.render(self.name, True, self.read_local('font.color'))
            surface.blit(text_surf, (abs_rect.x+5, abs_rect.y+5, abs_rect.width, abs_rect.height))

        for child in self.children:
            child.draw(surface)
    
    # Event Handlers
    
    def add_handler(self, event_type: str, handler: Callable) -> None:
        if event_type in self.events:
            self.events[event_type].append(handler)

    def remove_handler(self, event_type: str, handler: Callable) -> None:
        if event_type in self.events:
            self.events[event_type] = [h for h in self.events[event_type] if h != handler]
    
    # Geometry
    
    def get_absolute_rect(self) -> pygame.Rect:
        if self.cache_r is not None:
            return self.cache_r

        # Start with the element's local position
        x, y = self.rect.topleft
        parent = self.parent

        # Recursively add parent's absolute position
        if parent is not None:
            p_abs = parent.get_absolute_rect()
            x += p_abs.x
            y += p_abs.y

        # Create the absolute rect and cache it
        self.cache_r = pygame.Rect(x, y, self.rect.width, self.rect.height)
        return self.cache_r
    
    def is_inside(self, point: Tuple[int, int]) -> bool:
        return self.get_absolute_rect().collidepoint(point)

    def contains_point(self, point: Tuple[int, int]) -> bool:
        return self.is_inside(point)
        
    def read_local(self, name: str) -> Any:
        if self.has_local(name):
            return self.store[name]
        return None
        
    def write_local(self, name: str, value: Any) -> None:
        self.store[name] = value
    
    def has_local(self, name: str) -> bool:
        return (name in self.store)
    
    def get_db_length(self) -> int:
        return len(self.store)

# ############################################
#
# Element Class
# 
 
class UIElement(UIChassis):
    def __init__(self, x: int = 0, y: int = 0, width: int = 128, height: int = 64) -> None:
        self.name = self.__class__.__name__
        super().__init__(x, y, width, height)
        
    def _update_depth(self, new_depth: int) -> None:
        """Recursively update the depth of this element and all its children."""
        depth_change = new_depth - self.depth
        self.depth = new_depth
        for child in self.children:
            child._update_depth(child.depth + depth_change)

    # Overrides

    def contains_point(self, point: Tuple[int, int]) -> bool:
        if not self.visible:
            return False
        if super().contains_point(point):
            return True
        return any(child.contains_point(point) for child in self.children)

    # Event Handling

    def handle_event(self, event: pygame.event.Event) -> bool:
        for child in reversed(self.children):
            if child.handle_event(event):
                return True
        return self.process_event(event)

    def process_event(self, event: pygame.event.Event) -> bool:
        if self.passthrough:
            return False
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.process_mouse_button(event)
        elif event.type == pygame.MOUSEMOTION:
            return self.process_motion(event)
        elif event.type == pygame.KEYDOWN and self.active:
            return self.process_keypress(event)
        return False

    def process_motion(self, event: pygame.event.Event) -> bool:
        if self.is_inside(event.pos):
            self.trigger("hover", event)
            return True
        return False

    def process_keypress(self, event: pygame.event.Event) -> bool:
        self.trigger("keypress", event)
        return True

    def process_mouse_button(self, event: pygame.event.Event) -> bool:
        if self.is_inside(event.pos):
            # Only attempt to deactivate siblings if the parent is a UIElement (or UIRoot)
            # which has the deactivate method.
            if self.parent and hasattr(self.parent, 'deactivate'):
                self.parent.deactivate(self)
            if not self.active:
                self.active = True
                self.trigger("focus", event)
            self.trigger("click", event)
            return True
        elif self.active:
            self.active = False
            self.trigger("blur", event)
        return False

    def deactivate(self, root=None) -> None:
        for child in self.children:
            if child != root and child.active:
                child.active = False
                child.trigger("blur", pygame.event.Event(pygame.USEREVENT))

    def trigger(self, event_type: str, event: pygame.event.Event) -> None:
        for handler in self.events[event_type]:
            handler(self, event)

    # Generic controls

    def add(self, child: 'UIElement') -> None:
        if child is self or child.parent is self:
            return
        if child.depth < self.depth_max:
            self.children.append(child)
            child.parent = self
            child._update_depth(self.depth + 1) # Correct depth and propagate to children
            print(f'[{self.name}] parenting {child.name} depth: {child.depth}')
            self.reset()
            root = self.root()
            if self.connected(root):
                root.bus.register(child)

    def remove(self, child: 'UIElement') -> None:
        # Unregistering is handled in child.destroy()
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            self.reset()

    def destroy(self) -> None:
        """ Destroy branch and self """
        if self.disposed:
            return
        for child in list(self.children):
            child.destroy()
        
        # Unregister from bus before setting disposed to True
        root = self.root()
        if self.connected(root):
            root.bus.unregister(self)
            
        self.post(BROADCAST, Response.R_DISPOSED, attachment=self, priority=True)
        self.disposed = True
        if self.parent:
            self.parent.remove(self)
        self.children.clear()
        self.parent = None

    def reset(self) -> None:
        """ Reset propagation on local and branch caches """
        self.reset_graphics(recursive=False)
        self.cache = None
        self.reset_branch()
        
    def reset_branch(self) -> None:
        """ Reset propagation on branch caches """
        for child in self.children:
            child.reset()

    def reset_graphics(self, recursive: bool = True) -> None:
        """ Reset propagation on local and branch drawing cache shapes"""
        self.redraw = True
        self.cache_r = None
        if recursive:
            for child in self.children:
                child.reset_graphics(recursive)

    def reset_db(self, recursive: bool = True) -> None:
        """ Reset propagation on local and branch store cache"""
        self.store = {}
        if recursive:
            for child in self.children:
                child.reset_db(recursive)
    
    # Bus Messenger
    
    def root(self) -> 'UIElement':
        """ Traverse up stream to obtain root element (engine) """
        if self.cache is not None:
            return self.cache
        node = self
        while node.parent is not None:
            node = node.parent
        self.cache = node
        return node
        
    def connected(self, rt: 'UIElement') -> bool:
        """ Helper to verify root element has bus provisioning """
        return hasattr(rt, "bus") and rt.bus is not None
        
    def post(self, recv: int = BROADCAST, resp: Response = Response.R_OK,
        attachment: Any = None, priority: bool = False) -> None:
        """ Post message across element biome with set message parameters """
        root = self.root()
        if self.connected(root):
            packet = Packet(receiver=recv, sender=self.address, rs=resp, data=attachment)
            root.bus.post(packet)
            if priority:
                root.bus.pump()
                
    def handle_message(self, msg: Packet) -> None:
        """ Incoming message handling """
        if self.disposed or msg.sender == self.address:
            return
            
        if msg.rs == Response.R_GET:        # metadata sharing
            print(f'[{self.name}] Sending metadata...')
            self.post(msg.sender, Response.R_DATA,
                        attachment=self.get_metadata())
        elif msg.rs == Response.R_FONT:        # fonts
            self.store.update(msg.data)
        elif msg.rs == Response.R_VIS:       # visuals
            self.store.update(msg.data)
        elif msg.rs == Response.R_RESET:     # symbols reset
            self.reset()
        elif msg.rs == Response.R_TERMINATE: # termination
            self.destroy() 
        elif msg.rs == Response.R_CLEAR:    # reset assets
            self.reset_db(False)
        

    # Z-Order controls
    
    def bring_to_front(self) -> None:
        if not self.parent:
            return
        try:
            lst = self.parent.children
            lst.remove(self)
            lst.append(self)
            self.parent.reset()
        except ValueError:
            pass

    def send_to_back(self) -> None:
        if not self.parent:
            return
        try:
            lst = self.parent.children
            lst.remove(self)
            lst.insert(0, self)
            self.parent.reset()
        except ValueError:
            pass

    # Metadata

    def get_metadata(self) -> dict:
        metadata = {
            "name": self.name,
            "type": self.__class__.__name__,
            "address": self.address,
            "timeframe": time.time(),
            "x": self.rect.x,
            "y": self.rect.y,
            "width": self.rect.width,
            "height": self.rect.height,
            "visible": self.visible,
            "passthrough": self.passthrough,
            "disposed": self.disposed,
            "length": len(self.children),
            "container": [c.address for c in self.children],
        }
        if self.parent is not None:
            # metadata["parent"] = self.parent # Circular reference, better to avoid
            if hasattr(self.parent, 'address'):
                metadata["parent:address"] = self.parent.address
        return metadata
    
    # Properties

    @property
    def x(self) -> int:
        return self.rect.x

    @x.setter
    def x(self, value: int) -> None:
        self.rect.x = int(value)
        self.reset_graphics()
        self.reset()

    @property
    def y(self) -> int:
        return self.rect.y

    @y.setter
    def y(self, value: int) -> None:
        self.rect.y = int(value)
        self.reset_graphics()
        self.reset()

    @property
    def width(self) -> int:
        return self.rect.width

    @width.setter
    def width(self, value: int) -> None:
        self.rect.width = max(1, int(value))
        self.reset_graphics()
        self.reset()

    @property
    def height(self) -> int:
        return self.rect.height

    @height.setter
    def height(self, value: int) -> None:
        self.rect.height = max(1, int(value))
        self.reset_graphics()
        self.reset()

    @property
    def position(self) -> Tuple[int, int]:
        return (self.rect.x, self.rect.y)

    @position.setter
    def position(self, value: Tuple[int, int]) -> None:
        self.rect.x, self.rect.y = int(value[0]), int(value[1])
        self.reset_graphics()
        self.reset()

    @property
    def size(self) -> Tuple[int, int]:
        return (self.rect.width, self.rect.height)

    @size.setter
    def size(self, value: Tuple[int, int]) -> None:
        self.rect.width = max(1, int(value[0]))
        self.rect.height = max(1, int(value[1]))
        self.reset_graphics()
        self.reset()