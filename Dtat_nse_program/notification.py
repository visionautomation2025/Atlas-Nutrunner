from plyer import notification
import time

# First notification
notification.notify(
    title="Notification 1",
    message="bullish",
    timeout=5  # Duration in seconds
)
time.sleep(2)  # Wait for 2 seconds before showing the next notification

# Second notification
notification.notify(
    title="Notification 2",
    message="This is the second message!",
    timeout=5
)
time.sleep(2)  # Wait for 2 seconds before showing the next notification

# Third notification
notification.notify(
    title="Notification 3",
    message="This is the third message!",
    timeout=5
)