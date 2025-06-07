# pet_body.py

import tkinter as tk
from tkinter import simpledialog
import math
import random
import threading
import time

# --- NEW: Import Pillow for image handling ---
from PIL import Image, ImageTk

# Import the brain from the other file
from brain import Brain

# --- MODIFIED: Configuration Constants ---
IMAGE_SIZE = 60        # The size (width and height) to display the image
GRAVITY = 0.9
BOUNCE_FACTOR = 0.7
AIR_FRICTION = 0.995
GROUND_FRICTION = 0.9
UPDATE_INTERVAL = 15
EVENT_COOLDOWN = 5000

# --- Helper Functions ---
def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)


class BouncingBall:
    def __init__(self, canvas, screen_width, screen_height, ground_level):
        self.canvas = canvas
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.ground_level = ground_level

        # --- MODIFIED: Load and prepare the image ---
        self.photo_image = None
        try:
            pil_image = Image.open("softball.png")
            pil_image = pil_image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(pil_image)
        except FileNotFoundError:
            print("Error: softball.png not found! Make sure it's in the same directory. Falling back to a circle.")
        except Exception as e:
            print(f"Error loading image: {e}. Falling back to a circle.")

        # Physical properties based on image size
        self.radius = IMAGE_SIZE / 2
        self.x, self.y = screen_width / 2, screen_height / 4
        self.vx, self.vy = 5, 0

        # Create an image on the canvas, or a fallback circle
        if self.photo_image:
            self.id = self.canvas.create_image(self.x, self.y, image=self.photo_image)
        else:
            self.id = self.canvas.create_oval(self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius, fill="#c8c8c8", outline="")

        # Interaction properties
        self.is_dragging = False
        self.is_hovering = False
        self.last_mouse_x, self.last_mouse_y = 0, 0

        # Speech bubble properties
        self.bubble_rect_id = None
        self.bubble_text_id = None
        self.bubble_visible = False
        self.bubble_message = ""

        # Brain Integration
        self.brain = Brain()
        self.is_thinking = False
        self.last_event_time = 0

    # --- Core Logic ---
    def update(self):
        self._apply_physics()
        self._update_canvas_objects()

    def _apply_physics(self):
        if self.is_dragging:
            return
        self.vy += GRAVITY
        self.vx *= AIR_FRICTION
        self.vy *= AIR_FRICTION
        self.x += self.vx
        self.y += self.vy
        if self.y + self.radius >= self.ground_level:
            self.y = self.ground_level - self.radius
            self.vy *= -BOUNCE_FACTOR
            self.vx *= GROUND_FRICTION
            if abs(self.vy) < 1: self.vy = 0
        if self.x + self.radius >= self.screen_width or self.x - self.radius <= 0:
            self.vx *= -BOUNCE_FACTOR
            self.trigger_event("hit a wall")
            if self.x + self.radius >= self.screen_width: self.x = self.screen_width - self.radius
            else: self.x = self.radius
        if self.y - self.radius <= 0:
            self.y = self.radius
            self.vy *= -BOUNCE_FACTOR
            self.trigger_event("hit the ceiling")

    def _update_canvas_objects(self):
        # --- MODIFIED: Use new coordinates for the image center ---
        self.canvas.coords(self.id, self.x, self.y)
        if self.bubble_visible:
            self._redraw_speech_bubble()

    # --- Brain and Communication (Unchanged) ---
    def trigger_event(self, event_description: str):
        current_time = time.time() * 1000
        if (current_time - self.last_event_time) < EVENT_COOLDOWN:
            return
        self.last_event_time = current_time
        prompt = f"React to this event: You just {event_description}."
        self._think_in_background(prompt)

    def ask_brain(self, user_prompt: str):
        self._think_in_background(user_prompt)

    def _think_in_background(self, prompt: str):
        if self.is_thinking:
            return
        self.is_thinking = True
        thread = threading.Thread(target=self._ask_brain_thread, args=(prompt,), daemon=True)
        thread.start()

    def _ask_brain_thread(self, prompt: str):
        response = self.brain.get_response(prompt)
        self.canvas.after(0, self.say, response)
        self.is_thinking = False

    # --- Speech Bubble Management (Unchanged) ---
    def say(self, message: str, duration_ms: int = 4000):
        if self.bubble_visible: self.hide_bubble()
        self.bubble_message = message
        self.bubble_visible = True
        self.canvas.after(duration_ms, self.hide_bubble)

    def hide_bubble(self):
        if self.bubble_text_id: self.canvas.delete(self.bubble_text_id)
        if self.bubble_rect_id: self.canvas.delete(self.bubble_rect_id)
        self.bubble_rect_id = None
        self.bubble_text_id = None
        self.bubble_visible = False
        self.bubble_message = ""

    def _redraw_speech_bubble(self):
        if self.bubble_rect_id: self.canvas.delete(self.bubble_rect_id)
        if self.bubble_text_id: self.canvas.delete(self.bubble_text_id)
        bubble_x, bubble_y = self.x, self.y - self.radius - 30
        padding, corner_radius = 10, 15
        temp_text = self.canvas.create_text(-1000, -1000, text=self.bubble_message, font=("Arial", 10))
        text_bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x0 = bubble_x - text_width / 2 - padding
        y0 = bubble_y - text_height / 2 - padding
        x1 = bubble_x + text_width / 2 + padding
        y1 = bubble_y + text_height / 2 + padding
        self.bubble_rect_id = create_rounded_rectangle(self.canvas, x0, y0, x1, y1, radius=corner_radius, fill="white", outline="black")
        self.bubble_text_id = self.canvas.create_text(bubble_x, bubble_y, text=self.bubble_message, font=("Arial", 10), fill="black")

    # --- User Interaction Handlers (Unchanged) ---
    def check_hover(self, event):
        dist = math.sqrt((event.x - self.x)**2 + (event.y - self.y)**2)
        is_currently_over = (dist <= self.radius)
        if is_currently_over and not self.is_hovering:
            self.canvas.config(cursor="hand2")
            self.is_hovering = True
        elif not is_currently_over and self.is_hovering:
            self.canvas.config(cursor="")
            self.is_hovering = False

    def on_mouse_press(self, event):
        dist = math.sqrt((event.x - self.x)**2 + (event.y - self.y)**2)
        if dist <= self.radius:
            self.is_dragging = True
            self.vx, self.vy = 0, 0
            self.last_mouse_x, self.last_mouse_y = event.x, event.y
            self.trigger_event("being picked up")

    def on_mouse_drag(self, event):
        if self.is_dragging:
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            self.x += dx; self.y += dy
            self.vx = dx; self.vy = dy
            self.last_mouse_x, self.last_mouse_y = event.x, event.y

    def on_mouse_release(self, event):
        if self.is_dragging:
            self.is_dragging = False
            speed = math.sqrt(self.vx**2 + self.vy**2)
            if speed > 20: self.trigger_event("being thrown really fast")
            elif speed > 5: self.trigger_event("being tossed")
            else: self.trigger_event("being put down gently")


# --- Main Application Setup (Unchanged) ---
def main():
    root = tk.Tk()
    root.title("Desktop Pet")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.overrideredirect(True)
    root.wm_attributes("-topmost", True)
    transparent_color = 'grey15'
    root.wm_attributes("-transparentcolor", transparent_color)
    canvas = tk.Canvas(root, bg=transparent_color, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    taskbar_height_estimate = 50
    ground_level = screen_height - taskbar_height_estimate
    ball = BouncingBall(canvas, screen_width, screen_height, ground_level)
    canvas.bind("<ButtonPress-1>", ball.on_mouse_press)
    canvas.bind("<B1-Motion>", ball.on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", ball.on_mouse_release)
    canvas.bind("<Motion>", ball.check_hover)
    def close_app(event): root.destroy()
    root.bind("<Button-3>", close_app)
    def ask_pet_dialog(event):
        user_input = simpledialog.askstring("Talk to Pebble", "What do you want to say?")
        if user_input:
            ball.ask_brain(user_input)
    root.bind("<KeyPress-t>", ask_pet_dialog)
    canvas.focus_set()
    def game_loop():
        ball.update()
        if not ball.is_thinking and not ball.bubble_visible:
            if random.randint(1, 800) == 1:
                ball.trigger_event("got bored and had a random thought")
        root.after(UPDATE_INTERVAL, game_loop)
    game_loop()
    root.mainloop()

if __name__ == "__main__":
    main()