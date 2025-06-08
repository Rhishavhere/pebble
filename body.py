# body.py

import tkinter as tk
from tkinter import simpledialog, font
import math
import random
import threading
import time
from PIL import Image, ImageTk
from brain import Brain

# --- Configuration Constants ---
IMAGE_SIZE = 50
UPDATE_INTERVAL = 15      
EVENT_COOLDOWN = 1000     
FONT_CONFIG = ("Comic Neue", 10, "bold") 

# --- Physics Constants ---
GRAVITY = 0.9             
BOUNCE_FACTOR = 0.7      
AIR_FRICTION = 0.995     
GROUND_FRICTION = 0.9    

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    """Helper function to draw a rounded rectangle for the speech bubble."""
    points = [ x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1 ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

class BouncingBall:
    def __init__(self, canvas, screen_width, screen_height, ground_level):
        self.canvas = canvas
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.ground_level = ground_level

        # State and Image Management
        self.state = 'neutral'
        self.state_images = self._load_state_images()

        # Physical properties
        self.radius = IMAGE_SIZE / 2
        self.x, self.y = screen_width / 2, screen_height / 4
        self.vx, self.vy = random.choice([-5, 5]), 0

        # Create the initial image on the canvas
        initial_image = self.state_images.get(self.state, self.state_images['neutral'])
        self.id = self.canvas.create_image(self.x, self.y, image=initial_image)

        # Interaction properties
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.is_hovering = False

        # Bubble and brain properties
        self.bubble_rect_id, self.bubble_text_id = None, None
        self.bubble_visible, self.bubble_message = False, ""
        self.brain = Brain()
        self.is_thinking = False

        # Event queue properties
        self.last_event_time = 0
        self.pending_event = None
        self.event_trigger_time = 0

    def _load_state_images(self) -> dict:
        """Loads all pet images for different states."""
        images = {}
        states = ["neutral", "happy", "sad", "teary", "angry", "sleepy"]
        for state in states:
            try:
                pil_image = Image.open(f"images/pebble_{state}.png")
                pil_image = pil_image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.LANCZOS)
                images[state] = ImageTk.PhotoImage(pil_image)
            except FileNotFoundError:
                print(f"Warning: pebble_{state}.png not found.")

        if 'neutral' not in images:
            print("Fatal Error: pebble_neutral.png is required. Exiting.")
            self.canvas.master.destroy()
        return images

    def update(self):
        """Main update loop called every frame."""
        self._apply_physics()
        self._update_canvas_objects()

    def _apply_physics(self):
        """Applies gravity, friction, and handles collisions."""
        if self.is_dragging: return

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
            self.trigger_event("hit a wall")  # This will overwrite any pending "throw" event
            self.vx *= -BOUNCE_FACTOR
            if self.x + self.radius >= self.screen_width: self.x = self.screen_width - self.radius
            else: self.x = self.radius

        if self.y - self.radius <= 0:
            self.y = self.radius
            self.vy *= -BOUNCE_FACTOR

    def _update_canvas_objects(self):
        """Updates the position of the pet and its speech bubble on the canvas."""
        self.canvas.coords(self.id, self.x, self.y)
        if self.bubble_visible:
            self._redraw_speech_bubble()

    def trigger_event(self, event_description: str):
        """
        Sets a new physical event to be processed, overwriting any previous one.
        This does not call the brain directly; it adds the event to a queue.
        """
        if not self.is_thinking:
            self.pending_event = event_description
            self.event_trigger_time = time.time() * 1000

    def _process_pending_event(self):
        """
        Checks if a queued event exists and if cooldowns have passed, then sends it to the brain.
        This is called continuously by the main game loop.
        """
        if not self.pending_event or self.is_thinking:
            return

        current_time = time.time() * 1000
        # Wait a short moment (100ms) before processing to allow other events (like collision) to override.
        # Also, respect the main event cooldown.
        if (current_time - self.event_trigger_time > 100) and \
           (current_time - self.last_event_time > EVENT_COOLDOWN):

            event_to_process = self.pending_event
            self.pending_event = None  # Clear the queue
            self.last_event_time = current_time # Reset cooldown timer

            prompt = f"React to this event: You just {event_to_process}."
            self._think_in_background(prompt, self.brain.get_event_reaction)

    def ask_brain(self, user_prompt: str):
        """Handles user-initiated conversations, calling the conversational brain function."""
        self._think_in_background(user_prompt, self.brain.get_conversational_response)

    def _think_in_background(self, prompt: str, brain_method_to_call):
        """Starts a background thread to call a specific brain function."""
        if self.is_thinking: return
        self.is_thinking = True
        thread = threading.Thread(target=self._ask_brain_thread, args=(prompt, brain_method_to_call), daemon=True)
        thread.start()

    def _ask_brain_thread(self, prompt: str, brain_method):
        """The actual thread worker that calls the designated brain function."""
        brain_output = brain_method(prompt)
        self.canvas.after(0, self._process_brain_response, brain_output)
        self.is_thinking = False

    def _process_brain_response(self, brain_output: dict):
        """Processes the structured dictionary from the brain and applies the effects."""
        response = brain_output.get("response", "...")
        state = brain_output.get("state", "neutral")
        action = brain_output.get("action", "none")
        self.say(response)
        self.set_state(state)
        self.perform_action(action)

    def set_state(self, new_state: str):
        """Changes the pet's appearance based on its emotional state."""
        if new_state == self.state or new_state not in self.state_images: return
        self.state = new_state
        new_image = self.state_images[new_state]
        self.canvas.itemconfig(self.id, image=new_image)

    def perform_action(self, action_name: str):
        """Executes a physical action based on the brain's decision."""
        if self.is_dragging: return
        if action_name == "jump": self._action_jump()
        elif action_name == "slide": self._action_slide()

    def _action_jump(self):
        if self.y + self.radius >= self.ground_level - 5: self.vy = -20

    def _action_slide(self):
        self.vx += random.choice([-15, 15])

    # --- Mouse Interaction Methods ---
    def check_hover(self, event):
        dist = math.sqrt((event.x - self.x)**2 + (event.y - self.y)**2)
        is_currently_over = (dist <= self.radius)
        if is_currently_over and not self.is_hovering: self.canvas.config(cursor="hand2"); self.is_hovering = True
        elif not is_currently_over and self.is_hovering: self.canvas.config(cursor=""); self.is_hovering = False

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
            self.x += dx
            self.y += dy
            self.vx, self.vy = dx, dy
            self.last_mouse_x, self.last_mouse_y = event.x, event.y

    def on_mouse_release(self, event):
        if self.is_dragging:
            self.is_dragging = False
            speed = math.sqrt(self.vx**2 + self.vy**2)
            if speed > 20: self.trigger_event("being thrown really fast")
            elif speed > 5: self.trigger_event("being tossed")
            else: self.trigger_event("being put down gently")

    # --- Speech Bubble Methods ---
    def say(self, message: str, duration_ms: int = 4000):
        if self.bubble_visible: self.hide_bubble()
        self.bubble_message = message; self.bubble_visible = True
        self.canvas.after(duration_ms, self.hide_bubble)

    def hide_bubble(self):
        if self.bubble_text_id: self.canvas.delete(self.bubble_text_id)
        if self.bubble_rect_id: self.canvas.delete(self.bubble_rect_id)
        self.bubble_rect_id, self.bubble_text_id, self.bubble_visible, self.bubble_message = None, None, False, ""

    def _redraw_speech_bubble(self):
        if self.bubble_rect_id: self.canvas.delete(self.bubble_rect_id)
        if self.bubble_text_id: self.canvas.delete(self.bubble_text_id)
        
        bubble_x, bubble_y = self.x, self.y - self.radius - 30
        padding, corner_radius = 10, 15
        
        # Use the FONT_CONFIG constant to measure and draw the text
        temp_text = self.canvas.create_text(-1000, -1000, text=self.bubble_message, font=FONT_CONFIG)
        text_bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)
        
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x0 = bubble_x - text_width / 2 - padding
        y0 = bubble_y - text_height / 2 - padding
        x1 = bubble_x + text_width / 2 + padding
        y1 = bubble_y + text_height / 2 + padding
        
        self.bubble_rect_id = create_rounded_rectangle(self.canvas, x0, y0, x1, y1, radius=corner_radius, fill="white", outline="black")
        self.bubble_text_id = self.canvas.create_text(bubble_x, bubble_y, text=self.bubble_message, font=FONT_CONFIG, fill="black")

# --- Main Application Setup ---
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

    # Assume a taskbar height of about 50 pixels. Adjust if needed.
    ground_level = screen_height - 50

    ball = BouncingBall(canvas, screen_width, screen_height, ground_level)

    canvas.bind("<ButtonPress-1>", ball.on_mouse_press)
    canvas.bind("<B1-Motion>", ball.on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", ball.on_mouse_release)
    canvas.bind("<Motion>", ball.check_hover)

    def close_app(event): root.destroy()
    root.bind("<Button-3>", close_app)

    def ask_pet_dialog(event):
        if ball.is_thinking: return
        user_input = simpledialog.askstring("Pebble", "I love talking!!")
        if user_input: ball.ask_brain(user_input)
    root.bind("<KeyPress-t>", ask_pet_dialog)
    canvas.focus_set()

    def game_loop():
        ball.update()
        ball._process_pending_event() # Continuously check the event queue

        # Trigger a random thought only if nothing else is happening
        if not ball.is_thinking and not ball.bubble_visible and not ball.pending_event:
            if random.randint(1, 800) == 1:
                ball.trigger_event("think about something")   
        root.after(UPDATE_INTERVAL, game_loop)

    game_loop()
    root.mainloop()

if __name__ == "__main__":
    main()