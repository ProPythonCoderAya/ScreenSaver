import pygame
import time
import sys
import io

from objc import bool_property

pygame.init()

class BasePoolObject:
    def update(self, events):
        """Override this in subclasses to handle per-frame updates."""
        pass

    def draw(self, win):
        pass


class ObjectPool:
    def __init__(self):
        self.objects = []

    def add(self, obj: BasePoolObject):
        if not isinstance(obj, BasePoolObject):
            raise TypeError(f"Expected 'BasePoolObject', but got '{obj.__class__.__name__}'")
        self.objects.append(obj)

    def remove(self, obj: BasePoolObject):
        if obj in self.objects:
            self.objects.remove(obj)

    def clear(self):
        self.objects.clear()

    def update(self, events):
        for obj in self.objects:
            obj.update(events)

    def draw(self, win):
        for obj in self.objects:
            obj.draw(win)


class Button(BasePoolObject):
    def __init__(self, x, y, width, height, color, hover_color, text_color, text, font_size=20, font="comicsans", roundness=10):
        self.text_rect = None
        self.text_surf = None
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.hover_color = hover_color
        self.text = text
        self.roundness = roundness
        self._disabled = False
        self.font = font
        self.font_size = font_size
        self.text_color = text_color

        self.rect = pygame.Rect(x, y, width, height)
        self.rect.center = (x, y)

        self.change_text(text)

    def change_text(self, text):
        self.text = text
        font = pygame.font.SysFont(self.font, self.font_size)
        self.text_surf = font.render(self.text, 1, self.text_color)  # more speed
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    def draw(self, win):
        if self.disabled:
            color = (180, 180, 180)
        elif self.is_hovered():
            color = self.hover_color
        else:
            color = self.color
        temp_surf = pygame.Surface(self.rect[2:], pygame.SRCALPHA)
        temp_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(temp_surf, color, [0, 0, *self.rect[2:]], border_radius=self.roundness)

        win.blit(temp_surf, self.rect)
        win.blit(self.text_surf, self.text_rect)

    def is_hovered(self):
        if self.disabled:
            return False
        pos = pygame.mouse.get_pos()
        return self.rect.collidepoint(*pos)

    def is_clicked(self):
        if self.disabled:
            return False
        buttons = pygame.mouse.get_pressed()
        if not buttons[0]:
            return False
        return self.is_hovered()

    @property
    def disabled(self):
        return self._disabled

    def disable(self):
        self._disabled = True

    def enable(self):
        self._disabled = False


class TextBox(BasePoolObject):
    def __init__(self, x, y, width, height, max_chars, start_text, color, text_color, start_text_color, text_default="", font="comicsans", font_size=20, fit_to_text=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = max(font_size + 5, height)
        self.max_chars = max_chars
        self.start_text = start_text
        self.color = color
        self.text_color = text_color
        self.start_text_color = start_text_color
        self.font = pygame.font.SysFont(font, font_size)
        self.font_size = font_size
        self.text = text_default
        self.active = False
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.fit_to_text = fit_to_text

        self._cursor_visible = True
        self._last_blink = time.time()
        self._blink_interval = 0.5  # seconds

    def update(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.active = self.rect.collidepoint(event.pos)

            elif event.type == pygame.KEYDOWN and self.active:
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    char = event.unicode
                    if len(char) < 1 or ord(char) < 32:
                        continue
                    if len(self.text) < self.max_chars:
                        self.text += char

        # Update blinking
        if time.time() - self._last_blink >= self._blink_interval:
            self._cursor_visible = not self._cursor_visible
            self._last_blink = time.time()

    def draw(self, win):
        if self.text or self.active:
            font_surf = self.font.render(self.text, True, self.text_color)
        else:
            font_surf = self.font.render(self.start_text, True, self.start_text_color)

        text_pos = self.rect.copy()
        text_pos.x += 2.5
        text_pos.y -= 2

        rect = self.rect.copy()
        if self.fit_to_text:
            rect.width = font_surf.get_width() + 6
        pygame.draw.rect(win, self.color, rect, border_radius=5)
        win.blit(font_surf, text_pos)

        if self.active and self._cursor_visible:
            # Draw blinking cursor at the end of the text
            cursor_x = text_pos.x + font_surf.get_width()
            cursor_y = text_pos.y + 3
            cursor_height = self.font_size
            pygame.draw.line(win, self.text_color, (cursor_x, cursor_y + cursor_height), (cursor_x, cursor_y + 3), 2)


class Alert(BasePoolObject):
    def __init__(self, width: int, height: int, title: str, message: str, icon: str | bytes | pygame.Surface | None = None, button_names: tuple[str, str] | None = None):
        self.width: int = width
        self.height: int = height
        self.title: str = title
        self.message: str = message
        if icon is not None:
            if isinstance(icon, (str, bytes)):
                self.icon = pygame.image.load(icon).convert_alpha()
            elif isinstance(icon, pygame.Surface):
                self.icon = icon
            else:
                raise TypeError(f"Parameter 'icon' must be str, bytes, pygame.Surface or None, not '{type(icon)}'")
            self.icon = pygame.transform.scale(self.icon, (128, 128))
        else:
            self.icon = None
        if button_names:
            self.button_names = button_names
        else:
            self.button_names = ("Cancel", "Ok")  # Left-to-right

        self._result = None  # This will be one from self.button_names
        self._done = False
        self._fontS = pygame.font.SysFont(None, 24)
        self._fontL = pygame.font.SysFont(None, 30)
        w, h = pygame.display.get_window_size()
        self._rect = pygame.Rect(0, 0, width, height)
        self._rect.center = w / 2, h / 2
        bw, bh = 50 * 1.5, 20 * 1.5
        font_size = 30
        if self.icon is not None:
            self._rect.x -= 64
            if self.button_names[0] == "":
                self._button1 = Button(-100, -100, 0, 0, (0, 0, 0), (0, 0, 0), (0, 0, 0), "")
            else:
                self._button1 = Button(self._rect.x + 148 + bw / 2, self._rect.bottom - 20 - bh / 2, bw, bh, (220, 0, 0), (255, 0, 0),
                                    (0, 0, 0), self.button_names[0], font=None, font_size=font_size)
            if self.button_names[1] == "":
                self._button2 = Button(-100, -100, 0, 0, (0, 0, 0), (0, 0, 0), (0, 0, 0), "")
            else:
                self._button2 = Button(self._rect.right - 70 - bw / 2, self._rect.bottom - 20 - bh / 2, bw, bh, (0, 220, 0), (0, 255, 0),
                                    (0, 0, 0), self.button_names[1], font=None, font_size=font_size)
        else:
            if button_names[0] == "":
                self._button1 = Button(-100, -100, 0, 0, (0, 0, 0), (0, 0, 0), (0, 0, 0), "")
            else:
                self._button1 = Button(self._rect.x + 10 + bw / 2, self._rect.bottom - 20 - bh / 2, bw, bh, (220, 0, 0), (255, 0, 0),
                                       (0, 0, 0), self.button_names[0], font=None, font_size=font_size)
            if self.button_names[1] == "":
                self._button2 = Button(-100, -100, 0, 0, (0, 0, 0), (0, 0, 0), (0, 0, 0), "")
            else:
                self._button2 = Button(self._rect.right - 70 - bw / 2, self._rect.bottom - 20 - bh / 2, bw, bh, (0, 220, 0), (0, 255, 0),
                                       (0, 0, 0), self.button_names[1], font=None, font_size=font_size)
        self.pool = ObjectPool()
        self.pool.add(self._button1)
        self.pool.add(self._button2)

    def update(self, events):
        self.pool.update(events)
        if self._result is None:
            if self._button1.is_clicked():
                self._result = self.button_names[0]
                self._done = True
            if self._button2.is_clicked():
                self._result = self.button_names[1]
                self._done = True

    def done(self):
        return self._done

    @property
    def result(self):
        return self._result

    def draw(self, win):
        pygame.draw.rect(win, (127, 127, 127), self._rect, border_radius=15)

        if self.icon:
            win.blit(self.icon, (self._rect.x + 10, self._rect.centery - 64))

        title = self._fontL.render(self.title, True, (0, 0, 0))
        parts = []
        part = ""
        for char in self.message:
            part += char
            if char in "!?.":
                parts.append(part)
                part = ""
                continue
        message = []
        for part in parts:
            message.append(self._fontS.render(part.strip(), True, (0, 0, 0)))
        if self.icon:
            win.blit(title, (self._rect.x + 148, self._rect.y + 40))
            y = 0
            for part in message:
                win.blit(part, (self._rect.x + 148, self._rect.y + 70 + y))
                y += 24
        else:
            win.blit(title, (self._rect.x + 10, self._rect.y + 40))
            y = 0
            for part in message:
                win.blit(part, (self._rect.x + 10, self._rect.y + 70 + y))
                y += 24

        self.pool.draw(win)


class DoubleOut(io.TextIOBase):
    def __init__(self, file):
        self.file = open(file, "w", encoding="utf-8")
        self.stdout = sys.__stdout__

    def write(self, s):
        self.file.write(s)
        self.stdout.write(s)

    def flush(self):
        self.file.flush()
        self.stdout.flush()