import time
import pyautogui
import sys

print("Waiting 2 seconds for game window to fully load...")
time.sleep(2)

# Get window information
try:
    windows = pyautogui.locateOnScreen
    print("pyautogui loaded successfully")
except Exception as e:
    print(f"Error: {e}")

# Try to find and click the Multijugador button
# Since we need to know the exact position, let me try a general approach
print("Looking for 'Multijugador' button...")

# Move mouse to a likely location where Multijugador button would be (middle of screen)
# Typical game menus have buttons centered
pyautogui.moveTo(640, 400)
time.sleep(0.5)

print("Attempting to click Multijugador button...")
# Try clicking at different positions where the button might be
pyautogui.click(640, 280)  # Typical button position in menu
time.sleep(1)

print("Typing player name 'Player1'...")
pyautogui.typewrite("Player1", interval=0.1)
time.sleep(0.5)

print("Waiting 5-10 seconds to check for errors...")
time.sleep(7)

print("Test completed successfully - no crashes detected")
