import pygame
from enum import IntEnum
from typing import Tuple, Optional

from elements import UIElement
from bus import BROADCAST, Response

class Alignment(IntEnum):
    CENTER = 0
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4

# UIWindow        

class UIWindow(UIElement):
    def __init__(self, x: int, y: int, width: int, height: int, title: str = "Window"):
        super().__init__(x, y, width, height)
        self.title = title
        self.name = 'UIWindow'
        
        # Interaction states
        self.dragging = False
        self.drag_offset = (0, 0)
        self.resizing = False
        self.resize_start_pos = (0, 0)
        self.resize_start_size = (0, 0)
        
        # Layout constants
        self.titlebar_height = 24
        self.border_width = 2
        self.resize_corner_size = 12  
        
        # Base minimum size (can be overridden by children)
        self.base_min_size = (100, 60)
        
        # Window states
        self.active = True
        self.minimized = False
        self.maximized = False
        
        # Restore cache
        self.saved_rect = None
        
        # Clipping control
        self.clip_children = True  # Enable/disable child clipping
    
    
    # Public API
    
    
    def set_title(self, title: str) -> None:
        self.title = title
        self.reset_graphics()
    
    def minimize(self) -> None:
        if not self.minimized:
            self.minimized = True
            self.reset_graphics()
    
    def restore(self) -> None:
        if self.maximized and self.saved_rect:
            self.rect = self.saved_rect.copy()
            self.saved_rect = None
        self.minimized = False
        self.maximized = False
        self.reset_graphics()
    
    def maximize(self) -> None:
        if not self.maximized and self.parent:
            self.saved_rect = self.rect.copy()
            parent_rect = self.parent.get_absolute_rect()
            self.rect = pygame.Rect(0, 0, parent_rect.width, parent_rect.height)
            self.maximized = True
            self.reset_graphics()
    
    def get_min_size(self) -> Tuple[int, int]:
        """Calculate minimum size based on base minimum and children bounds"""
        min_width, min_height = self.base_min_size
        
        if not self.children:
            return (min_width, min_height)
        
        # Calculate the bounding box of all children
        max_child_right = 0
        max_child_bottom = 0
        
        for child in self.children:
            if child.visible and not child.disposed:
                # Child position is relative to parent
                child_right = child.rect.x + child.rect.width
                child_bottom = child.rect.y + child.rect.height
                
                max_child_right = max(max_child_right, child_right)
                max_child_bottom = max(max_child_bottom, child_bottom)
        
        # Add padding for titlebar and borders
        content_padding = (self.border_width + 1) * 2
        required_width = max_child_right + content_padding
        required_height = max_child_bottom + self.titlebar_height + content_padding
        
        # Return the maximum of base minimum and required size
        return (
            max(min_width, required_width),
            max(min_height, required_height)
        )
    
    def get_content_rect(self) -> pygame.Rect:
        """Get the absolute rect of the content area (for clipping)"""
        abs_rect = self.get_absolute_rect()
        return pygame.Rect(
            abs_rect.x + self.border_width + 1,
            abs_rect.y + self.titlebar_height + self.border_width + 1,
            abs_rect.width - (self.border_width + 1) * 2,
            abs_rect.height - self.titlebar_height - (self.border_width + 1) * 2
        )
    
    
    # Drawing with Clipping
    

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible or self.disposed:
            return
        
        if self.minimized:
            self._draw_minimized(surface)
            return
        
        # Draw window chrome (frame, titlebar, content bg)
        self._draw_frame(surface)
        self._draw_titlebar(surface)
        self._draw_content(surface)
        
        # Draw children with clipping
        if self.clip_children:
            self._draw_children_clipped(surface)
        else:
            # Fallback: draw without clipping
            for child in self.children:
                child.draw(surface)
    
    def _draw_children_clipped(self, surface: pygame.Surface) -> None:
        """Draw children with clipping to content area"""
        if not self.children:
            return
        
        content_rect = self.get_content_rect()
        
        # Store original clip
        original_clip = surface.get_clip()
        
        # Set clip to content area
        # If there's already a clip, intersect with it
        if original_clip:
            clipped_rect = content_rect.clip(original_clip)
        else:
            clipped_rect = content_rect
        
        surface.set_clip(clipped_rect)
        
        # Draw all children (they'll be clipped)
        for child in self.children:
            child.draw(surface)
        
        # Restore original clip
        surface.set_clip(original_clip)
    
    def _draw_minimized(self, surface: pygame.Surface) -> None:
        """Draw minimized window as taskbar button"""
        if not self.has_local('frame.active'):
            return
        
        abs_rect = self.get_absolute_rect()
        mini_rect = pygame.Rect(abs_rect.x, abs_rect.y, 150, self.titlebar_height)
        
        title_color = self.read_local('title.inactive')
        pygame.draw.rect(surface, title_color, mini_rect)
        pygame.draw.rect(surface, self.read_local('bevel.shadow'), mini_rect, 1)
        
        if self.has_local('font'):
            font = self.read_local('font')
            text = font.render(self.title, True, self.read_local('title.text'))
            surface.blit(text, (mini_rect.x + 5, mini_rect.y + 4))
    
    def _draw_frame(self, surface: pygame.Surface) -> None:
        """Draw window border with 3D bevel effect"""
        if not self.has_local('bevel.high'):
            return
        
        abs_rect = self.get_absolute_rect()
        high = self.read_local('bevel.high')
        face = self.read_local('bevel.face')
        shadow = self.read_local('bevel.shadow')
        dark = self.read_local('bevel.dark')
        
        # Base 
        pygame.draw.rect(surface, dark, abs_rect)
        
        # Outer raised bevel
        pygame.draw.line(surface, high, abs_rect.topleft, abs_rect.topright, 1)
        pygame.draw.line(surface, high, abs_rect.topleft, abs_rect.bottomleft, 1)
        pygame.draw.line(surface, shadow, abs_rect.bottomright, abs_rect.topright, 1)
        pygame.draw.line(surface, shadow, abs_rect.bottomright, abs_rect.bottomleft, 1)
        
        # Inner bevel
        inner = abs_rect.inflate(-2, -2)
        pygame.draw.line(surface, dark, inner.topleft, inner.topright, 1)
        pygame.draw.line(surface, dark, inner.topleft, inner.bottomleft, 1)
        pygame.draw.line(surface, face, inner.bottomright, inner.topright, 1)
        pygame.draw.line(surface, face, inner.bottomright, inner.bottomleft, 1)
    
    def _draw_titlebar(self, surface: pygame.Surface) -> None:
        """Draw title bar with gradient and title text"""
        if not self.has_local('title.active'):
            return
        
        abs_rect = self.get_absolute_rect()
        title_color = self.read_local('title.active') if self.active else self.read_local('title.inactive')
        
        title_rect = pygame.Rect(
            abs_rect.x + self.border_width,
            abs_rect.y + self.border_width,
            abs_rect.width - self.border_width * 2,
            self.titlebar_height
        )
        pygame.draw.rect(surface, title_color, title_rect)
        
        # Caption
        if self.has_local('font'):
            font = self.read_local('font')
            text_color = self.read_local('title.text')
            text = font.render(self.title, True, text_color)
            surface.blit(text, (title_rect.x + 5, title_rect.y + 4))
    
    def _draw_content(self, surface: pygame.Surface) -> None:
        """Draw window content area background"""
        if not self.has_local('content.bg'):
            return
        
        content_rect = self.get_content_rect()
        bg_color = self.read_local('content.bg')
        pygame.draw.rect(surface, bg_color, content_rect)
        
        # Draw resizer
        if not self.maximized:
            self._draw_resizer(surface, content_rect)
    
    def _draw_resizer(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        shadow = self.read_local('bevel.shadow')
        corner_x = rect.right - self.resize_corner_size
        corner_y = rect.bottom - self.resize_corner_size
        for i in range(3):
            offset = i * 4 + 2
            pygame.draw.line(surface, shadow, 
                (corner_x + offset, rect.bottom - 2),
                (rect.right - 2, corner_y + offset), 2)
    
    
    # Event Handling
    
    
    def process_mouse_button(self, event: pygame.event.Event) -> bool:
        if self.minimized:
            if event.button == 1 and self.is_inside(event.pos):
                self.restore()
                return True
            return False
        
        abs_rect = self.get_absolute_rect()
        
        # Mouse down
        if event.button == 1:
            # Check resize corner first
            if not self.maximized and self._hitbox_resizer(event.pos, abs_rect):
                self.resizing = True
                self.resize_start_pos = event.pos
                self.resize_start_size = (self.rect.width, self.rect.height)
                self.bring_to_front()
                return True
            
            # Check titlebar for dragging
            if self._hitbox_titlebar(event.pos, abs_rect):
                if not self.maximized:
                    self.dragging = True
                    self.drag_offset = (event.pos[0] - abs_rect.x, event.pos[1] - abs_rect.y)
                self.bring_to_front()
                return True
            
            # Handle click
            if self.is_inside(event.pos):
                self.bring_to_front()
                return super().process_mouse_button(event)
        
        return False
    
    def process_motion(self, event: pygame.event.Event) -> bool:
        if self.dragging:
            self._process_dragging(event.pos)
            #self.snap_on()
            return True
        
        if self.resizing:
            self._handle_resize(event.pos)
            return True
        
        # Change cursor
        if not self.maximized:
            abs_rect = self.get_absolute_rect()
            if self._hitbox_resizer(event.pos, abs_rect):
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENWSE)
                return True
            else:
                if pygame.mouse.get_cursor() != pygame.SYSTEM_CURSOR_ARROW:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        
        return super().process_motion(event)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        # Handle mouse button up
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging or self.resizing:
                self.dragging = False
                self.resizing = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return True
        
        return super().handle_event(event)
    
    
    # Interaction Helpers
    
    
    def _hitbox_titlebar(self, pos: Tuple[int, int], abs_rect: pygame.Rect) -> bool:
        """Check if position is within titlebar"""
        return (abs_rect.x <= pos[0] <= abs_rect.right and
                abs_rect.y <= pos[1] <= abs_rect.y + self.titlebar_height + self.border_width)
    
    def _hitbox_resizer(self, pos: Tuple[int, int], abs_rect: pygame.Rect) -> bool:
        """Check if position is within bottom-right resize corner"""
        return (abs_rect.right - self.resize_corner_size <= pos[0] <= abs_rect.right and
                abs_rect.bottom - self.resize_corner_size <= pos[1] <= abs_rect.bottom)
    
    def _process_dragging(self, mouse_pos: Tuple[int, int]) -> None:
        """Handle window dragging"""
        # Calculate absolute position
        new_abs_x = mouse_pos[0] - self.drag_offset[0]
        new_abs_y = mouse_pos[1] - self.drag_offset[1]
        
        # Get parent's absolute offset
        parent_abs_x, parent_abs_y = 0, 0
        if self.parent:
            parent_abs_rect = self.parent.get_absolute_rect()
            parent_abs_x, parent_abs_y = parent_abs_rect.topleft
        
        # Convert to relative
        new_rel_x = new_abs_x - parent_abs_x
        new_rel_y = new_abs_y - parent_abs_y
        
        # Clamp to parent bounds
        if self.parent and isinstance(self.parent, UIElement):
            parent_rect = self.parent.rect
            new_rel_x = max(0, min(new_rel_x, parent_rect.width - self.rect.width))
            new_rel_y = max(0, min(new_rel_y, parent_rect.height - 30))
        
        self.position = (new_rel_x, new_rel_y)
    
    def _handle_resize(self, mouse_pos: Tuple[int, int]) -> None:
        """Handle window resizing with minimum size constraints"""
        delta_x = mouse_pos[0] - self.resize_start_pos[0]
        delta_y = mouse_pos[1] - self.resize_start_pos[1]
        
        # Get minimum size based on children
        min_width, min_height = self.get_min_size()
        
        # Calculate new size respecting minimum
        new_width = max(min_width, self.resize_start_size[0] + delta_x)
        new_height = max(min_height, self.resize_start_size[1] + delta_y)
        
        # Clamp to parent bounds
        if self.parent:
            parent_rect = self.parent.get_absolute_rect()
            abs_rect = self.get_absolute_rect()
            max_width = parent_rect.width - abs_rect.x
            max_height = parent_rect.height - abs_rect.y
            new_width = min(new_width, max_width)
            new_height = min(new_height, max_height)
        
        self.size = (new_width, new_height)
    
    
    # Snap-On
    
    
    def snap_on(self, threshold: int = 10) -> None:
        """Snap window edges to nearby sibling windows"""
        if not self.parent:
            return
        siblings = [child for child in self.parent.children
            if child is not self and child.visible and not child.disposed]
        
        if not siblings:
            return
        
        my_rect = self.get_absolute_rect()
        
        for win in siblings:
            their_rect = win.get_absolute_rect()
            
            # Horizontal snapping
            if abs(my_rect.left - their_rect.left) <= threshold:
                dx = their_rect.left - my_rect.left
                self.x += dx
            elif abs(my_rect.right - their_rect.right) <= threshold:
                dx = their_rect.right - my_rect.right
                self.x += dx
            
            # Vertical snapping
            if abs(my_rect.top - their_rect.top) <= threshold:
                dy = their_rect.top - my_rect.top
                self.y += dy
            elif abs(my_rect.bottom - their_rect.bottom) <= threshold:
                dy = their_rect.bottom - my_rect.bottom
                self.y += dy
    
    
    # Z-Order Override
    
    
    def bring_to_front(self) -> None:
        """Bring window to front and activate it"""
        super().bring_to_front()
        if not self.active:
            self.active = True
            self.reset_graphics()
            
            # Deactivate sibling windows
            if self.parent:
                for sibling in self.parent.children:
                    if sibling != self and isinstance(sibling, UIWindow) and sibling.active:
                        sibling.active = False
                        sibling.reset_graphics()