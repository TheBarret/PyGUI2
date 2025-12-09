from __future__ import annotations
import pygame
import time
import json
import os
import random
import traceback
from typing import List, Any, Tuple, Callable, Optional

from elements import UIElement
from bus import BROADCAST, Response, Packet, AddressBus


class UIRoot(UIElement):
    __slots__ = ('clock', 'surface', 'fps', 'running', 'bus', 
             'bus_freq', 'bus_accumulator', 'current_fps', 'frame_count')
    def __init__(self, width: int = 800, height: int = 600, fps: int = 60, title: str = "root", bus_freq: float = 0.3):
        super().__init__(0, 0, width, height)
        pygame.init()
        pygame.display.set_caption(title)
        self.name = 'UIRoot'
        self.clock = pygame.time.Clock()
        self.surface: pygame.Surface = pygame.display.set_mode((width, height), 0)
        self.fps = fps
        self.running = False
        self.bus = AddressBus()
        self.bus_freq = bus_freq
        self.bus_accumulator = 0.0
        self.bus.register(self)
        self.current_fps = 0
        self.frame_count = 0
                
    def root(self) -> UIElement:
        return self
    
    def add(self, child: UIElement) -> None:
        super().add(child)
        child.parent = self
        
    def run(self) -> None:
        self.running = True
        try:
            while self.running or len(self.children) > 0:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.destroy()
                        continue
                    self.handle_event(event)
                
                dt = self.clock.tick(self.fps) / 1000.0
                
                # stats
                self.current_fps = self.clock.get_fps()
                self.frame_count += 1
                
                # throttle bus pump
                self.bus_accumulator += dt
                if self.bus_accumulator >= self.bus_freq:
                    self.bus.pump()
                    self.bus_accumulator -= self.bus_freq
                
                self.update(dt)
                 
                self.surface.fill((0, 0, 0))
                self.draw(self.surface)
                
                pygame.display.flip()
        except KeyboardInterrupt:
            print("[root] Interrupted...")
            self.destroy()
        except Exception as e:
            print(f"Fatal exception:\n{e}")
            print(f"Stack:\n{traceback.format_exc()}")
            self.destroy()
        finally:
            print('[root] quit')
            pygame.quit()    
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.destroy()
                return True
        return super().handle_event(event)

    def destroy(self) -> None:
        self.post(BROADCAST, Response.R_CLEAR, priority=True)
        self.post(BROADCAST, Response.R_RESET, priority=True)
        self.post(BROADCAST, Response.R_TERMINATE, priority=True)
        self.running = False
        
    def handle_message(self, msg: Packet) -> None:
        super().handle_message(msg)
        
    def get_metadata(self) -> dict:
        md = super().get_metadata()
        md["fps"] = self.fps
        md["bus_freq"] = self.bus_freq
        md["current_fps"] = self.current_fps
        md["frame_count"] = self.frame_count
        return md
        
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__},name={self.name},addr={self.address},bus_freq={self.bus_freq}hz>"

class UIFont(UIElement):
    def __init__(self):
        super().__init__(1, 1, 10, 10)
        self.name = 'UIFont'
        self.visible = False
    
    def initialize(self, name: str, size: int = 24) -> None:
            path = os.path.join("assets", f"{name}")
            _font = pygame.font.Font(path, size)
            self.store['font'] = _font
            self.post(BROADCAST, Response.R_FONT, attachment=self.store)

class UIVisuals(UIElement):
    def __init__(self):
        super().__init__(1, 1, 10, 10)
        self.name = 'UIVisuals'
        self.visible = False
    
    def initialize(self) -> None:
        self.store['frame.active'] = (0, 60, 116)
        self.store['frame.inactive'] = (161, 161, 146)
        self.store['frame.border'] = (200, 200, 146)
        self.store['font.color'] = (255, 255, 255)
        
        # Bevel
        self.store['bevel.high'] = (255, 255, 255)      # Highlight
        self.store['bevel.face'] = (236, 233, 216)      # Face color
        self.store['bevel.shadow'] = (172, 168, 153)    # Shadow
        self.store['bevel.dark'] = (128, 128, 112)      # Dark shadow
        
        # Titlebar
        self.store['title.active'] = (0, 60, 116)       # Active window title
        self.store['title.inactive'] = (161, 161, 146)  # Inactive window title
        self.store['title.text'] = (255, 255, 255)      # Title text
        
        # Content
        self.store['content.bg'] = (236, 233, 216)      # Window content background
        
        # Buttons
        self.store['button.face'] = (236, 233, 216)     # Normal button face
        self.store['button.hover'] = (220, 220, 205)    # Hover state
        self.store['button.pressed'] = (180, 180, 170)  # Pressed state
        self.store['button.disabled'] = (200, 200, 200) # Disabled state
        self.store['button.text'] = (0, 0, 0)           # Button text color
        self.store['button.text.disabled'] = (128, 128, 128)  # Disabled text
        
        # Input fields
        self.store['input.bg'] = (255, 255, 255)        # Input background
        self.store['input.border'] = (128, 128, 112)    # Input border
        self.store['input.text'] = (0, 0, 0)            # Input text
        self.store['input.placeholder'] = (160, 160, 160)  # Placeholder text
        
        # Selection
        self.store['selection.bg'] = (0, 60, 116)       # Selection background
        self.store['selection.text'] = (255, 255, 255)  # Selection text
        
        # announce
        self.post(BROADCAST, Response.R_VIS, attachment=self.store)
