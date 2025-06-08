# body.py

import tkinter as tk
from tkinter import simpledialog
import math
import random
import threading
import time
from PIL import Image, ImageTk
from brain import Brain

# --- Configuration Constants ---
IMAGE_SIZE = 60
UPDATE_INTERVAL = 15  # ms per frame update
EVENT_COOLDOWN = 5000 # ms between random events

### NEW/MODIFIED: Physics Constants ###
GRAVITY = 0.9          # How fast the pet accelerates downwards
BOUNCE_FACTOR = 0.7    # How much velocity is kept after a bounce (0=none, 1=perfect)
AIR_FRICTION = 0.995   # Slows down movement in the air (1.0 = no friction)
GROUND_FRICTION = 0.9  # Slows down horizontal movement on the ground (1.0 = no friction)


def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [ x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1 ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

class BouncingBall:
    def __init__(self, canvas, screen_width, screen_height, ground_level):
        self.canvas = canvas
        self.screen_width = screen_width
        self.screen_height = screen_height
        ### NEW/MODIFIED: The ground_level is now essential for physics ###
        self.ground_level = ground_level

        # State and Image Management
        self.state = 'neutral'
        self.state_images = self._load_state_images()

        # Physical properties
        self.radius = IMAGE_SIZE / 2
        self.x, self.y = screen_width / 2, screen_height / 4
        # Start with a little horizontal motion
        self.vx, self.vy = random.choice([-5, 5]), 0

        # Create the initial image on the canvas
        initial_image = self.state_images.get(self.state, self.state_images['neutral'])
        self.id = self.canvas.create_image(self.x, self.y, image=initial_image)

        # Interaction properties
        ### NEW/MODIFIED: Added properties for dragging ###
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.is_hovering = False

        # Bubble and brain properties
        self.bubble_rect_id, self.bubble_text_id = None, None
        self.bubble_visible, self.bubble_message = False, ""
        self.brain = Brain()
        self.is_thinking, self.last_event_time = False, 0

    def _load_state_images(self) -> dict:
        """Loads all pet images for different states."""
        images = {}
        states = ["neutral", "happy", "sad", "teary","angry","sleepy"]
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
        ### NEW/MODIFIED: The core logic is now split ###
        self._apply_physics()
        self._update_canvas_objects()

    ### NEW/MODIFIED: All physics logic is now in this method ###
    def _apply_physics(self):
        """Applies gravity, friction, and handles collisions."""
        # Don't apply physics if the user is dragging the pet
        if self.is_dragging:
            return

        # 1. Apply Gravity
        self.vy += GRAVITY

        # 2. Apply Air Friction
        self.vx *= AIR_FRICTION
        self.vy *= AIR_FRICTION

        # 3. Update Position
        self.x += self.vx
        self.y += self.vy

        # 4. Ground Collision and Bounce
        if self.y + self.radius >= self.ground_level:
            self.y = self.ground_level - self.radius  # Snap to ground
            self.vy *= -BOUNCE_FACTOR  # Reverse and dampen vertical velocity
            self.vx *= GROUND_FRICTION # Apply ground friction
            
            # Come to a complete stop if moving very slowly vertically
            if abs(self.vy) < 1:
                self.vy = 0

        # 5. Wall Collisions
        if self.x + self.radius >= self.screen_width or self.x - self.radius <= 0:
            # Trigger an event, but not constantly
            if not self.is_thinking:
                self.trigger_event("hit a wall")
            self.vx *= -BOUNCE_FACTOR # Bounce off the wall
            # Snap to screen edge to prevent getting stuck
            if self.x + self.radius >= self.screen_width:
                self.x = self.screen_width - self.radius
            else:
                self.x = self.radius

        # 6. Ceiling Collision
        if self.y - self.radius <= 0:
            self.y = self.radius
            self.vy *= -BOUNCE_FACTOR


    def _update_canvas_objects(self):
        """Updates the position of the pet and its speech bubble on the canvas."""
        self.canvas.coords(self.id, self.x, self.y)
        if self.bubble_visible:
            self._redraw_speech_bubble()

    def trigger_event(self, event_description: str):
        """Makes the pet react to a physical event."""
        current_time = time.time() * 1000
        if (current_time - self.last_event_time) < EVENT_COOLDOWN:
            return
        self.last_event_time = current_time
        prompt = f"React to this event: You just {event_description}."
        self._think_in_background(prompt)

    # --- Interaction Methods (Mouse) ---

    def check_hover(self, event):
        """Changes the cursor when hovering over the pet."""
        dist = math.sqrt((event.x - self.x)**2 + (event.y - self.y)**2)
        is_currently_over = (dist <= self.radius)
        if is_currently_over and not self.is_hovering:
            self.canvas.config(cursor="hand2")
            self.is_hovering = True
        elif not is_currently_over and self.is_hovering:
            self.canvas.config(cursor="")
            self.is_hovering = False

    ### NEW/MODIFIED: Handle starting a drag ###
    def on_mouse_press(self, event):
        """Called when the user clicks the mouse."""
        dist = math.sqrt((event.x - self.x)**2 + (event.y - self.y)**2)
        if dist <= self.radius:
            self.is_dragging = True
            # Stop all momentum when picked up
            self.vx, self.vy = 0, 0
            self.last_mouse_x, self.last_mouse_y = event.x, event.y
            self.trigger_event("being picked up")

    ### NEW/MODIFIED: Handle dragging the pet ###
    def on_mouse_drag(self, event):
        """Called when the user moves the mouse while holding the button."""
        if self.is_dragging:
            # Calculate how much the mouse has moved
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            
            # Move the pet by that amount
            self.x += dx
            self.y += dy
            
            # IMPORTANT: Store the delta as velocity for the "throw"
            self.vx = dx
            self.vy = dy
            
            # Update the last mouse position for the next frame
            self.last_mouse_x, self.last_mouse_y = event.x, event.y

    ### NEW/MODIFIED: Handle releasing the pet ###
    def on_mouse_release(self, event):
        """Called when the user releases the mouse button."""
        if self.is_dragging:
            self.is_dragging = False
            # The vx and vy are already set from the last drag event
            
            # Trigger an event based on the speed of the throw
            speed = math.sqrt(self.vx**2 + self.vy**2)
            if speed > 10:
                self.trigger_event("being thrown really fast")
            elif speed > 3:
                self.trigger_event("being tossed")
            else:
                self.trigger_event("being put down gently")

    # --- Brain, State, and Action Methods ---

    def ask_brain(self, user_prompt: str):
        self._think_in_background(user_prompt)

    def _think_in_background(self, prompt: str):
        if self.is_thinking: return
        self.is_thinking = True
        thread = threading.Thread(target=self._ask_brain_thread, args=(prompt,), daemon=True)
        thread.start()

    def _ask_brain_thread(self, prompt: str):
        brain_output = self.brain.get_response(prompt)
        self.canvas.after(0, self._process_brain_response, brain_output)
        self.is_thinking = False

    def _process_brain_response(self, brain_output: dict):
        response = brain_output.get("response", "...")
        state = brain_output.get("state", "neutral")
        action = brain_output.get("action", "none")
        self.say(response)
        self.set_state(state)
        self.perform_action(action)

    def set_state(self, new_state: str):
        if new_state == self.state or new_state not in self.state_images: return
        self.state = new_state
        new_image = self.state_images[new_state]
        self.canvas.itemconfig(self.id, image=new_image)

    def perform_action(self, action_name: str):
        if self.is_dragging: return
        if action_name == "jump": self._action_jump()
        elif action_name == "slide": self._action_slide()

    def _action_jump(self):
        # Only jump if on or very near the ground
        if self.y + self.radius >= self.ground_level - 5:
            self.vy = -20  # Strong upward velocity

    def _action_slide(self):
        self.vx += random.choice([-15, 15])

    # --- Speech Bubble Methods (Unchanged) ---
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
        temp_text = self.canvas.create_text(-1000, -1000, text=self.bubble_message, font=("Comic Neue", 10, "bold"))
        text_bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x0 = bubble_x - text_width / 2 - padding
        y0 = bubble_y - text_height / 2 - padding
        x1 = bubble_x + text_width / 2 + padding
        y1 = bubble_y + text_height / 2 + padding
        self.bubble_rect_id = create_rounded_rectangle(self.canvas, x0, y0, x1, y1, radius=corner_radius, fill="white", outline="black")
        self.bubble_text_id = self.canvas.create_text(bubble_x, bubble_y, text=self.bubble_message, font=("Comic Neue", 10, "bold"), fill="black")


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

    # Ground Height
    ground_level = screen_height - 50

    ball = BouncingBall(canvas, screen_width, screen_height, ground_level)

    # Bind all the necessary mouse events
    canvas.bind("<ButtonPress-1>", ball.on_mouse_press)
    canvas.bind("<B1-Motion>", ball.on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", ball.on_mouse_release)
    canvas.bind("<Motion>", ball.check_hover) 

    def close_app(event):
        root.destroy()
    root.bind("<Button-3>", close_app)

    def ask_pet_dialog(event):
        if ball.is_thinking: return
        user_input = simpledialog.askstring("Talk to Pebble", "What do you want to say?")
        if user_input:
            ball.ask_brain(user_input)
    root.bind("<KeyPress-t>", ask_pet_dialog)
    canvas.focus_set()

    def game_loop():
        ball.update()
        # Random thought logic
        if not ball.is_thinking and not ball.bubble_visible:
            if random.randint(1, 300) == 1:
                ball.trigger_event("got bored")
        root.after(UPDATE_INTERVAL, game_loop)

    game_loop()
    root.mainloop()

if __name__ == "__main__":
    main()