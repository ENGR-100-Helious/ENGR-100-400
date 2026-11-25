from pupil_apriltags import Detector
import cv2
import socket
import numpy as np
import time

APRIL_TAG_IP = "192.168.50.213"
LINE_FOLLOW_IP = "192.168.50.214"
TCP_PORT = 5005
CONNECT_TIMEOUT = 3
SEND_TIMEOUT = 2
RECONNECT_DELAY = 1
MAX_VIDEO_FAILURES = 5

isAtFork = False
isAtShelf = False
angle_weight = 10


def socket_setup():
    """Connect to the ESP32, retrying until successful."""
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(CONNECT_TIMEOUT)

        try:
            print(
                f"Connecting to ESP32 at "
                f"{APRIL_TAG_IP}:{TCP_PORT}..."
            )
            sock.connect((LINE_FOLLOW_IP, TCP_PORT))

            # Use a blocking socket with a timeout.
            # Do NOT use setblocking(False) with sendall().
            sock.settimeout(SEND_TIMEOUT)

            print("Successfully connected to ESP32.")
            return sock

        except OSError as e:
            print(f"Connection failed: {e}")
            sock.close()
            time.sleep(RECONNECT_DELAY)

def send_command(sock, message):
    """Send a command and reconnect automatically if the socket fails."""
    while True:
        try:
            sock.sendall(message.encode("utf-8"))
            return sock

        except (OSError, TimeoutError) as e:
            print(f"Socket send failed: {e}")
            print("Reconnecting to ESP32...")

            try:
                sock.close()
            except OSError:
                pass

            # Wait for a new connection, then retry the command.
            sock = socket_setup()

def open_video(url):


    print(f"Opening camera stream: {url}", flush=True)

    vid = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

    if not vid.isOpened():
        print("Camera stream unavailable", flush=True)
        vid.release()
        return None

    return vid

def getAprilTagIDs(detector, frame):
    # Convert BGR image to grayscale
    gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # cv2.imshow("gray", gray_img)
    # if cv2.waitKey(1) & 0xFF == ord('q'):
    #     break
    
    # Detect AprilTags
    result = detector.detect(gray_img)

    if len(result) > 0:
        for tag in result:
            print("Tag ID:", tag.tag_id)
    else:
        print("No AprilTags detected")

# --------------------------------------------------
# Helper function: Detect and fit a line in one region
# --------------------------------------------------
def detect_line_in_region(mask, x_offset, full_width):

    height, region_width = mask.shape

    # Find contours within this region only.
    contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

    if not contours:
        return None, None, None, None

    # Ignore contours that are too small to be the tape.
    min_area = max(30, height * region_width * 0.001)

    valid = [
            c for c in contours
            if cv2.contourArea(c) > min_area
        ]

    if not valid:
        return None, None, None, None

    # Select the largest valid orange contour in this region.
    candidate = max(valid, key=cv2.contourArea)

    # Create a mask containing only this contour.
    clean_mask = np.zeros_like(mask)

    cv2.drawContours(
            clean_mask,
            [candidate],
            -1,
            255,
            -1
        )

    points = []

    # Find the center of the orange contour at every row.
    for y in range(height):

        xs = np.where(clean_mask[y] > 0)[0]

        if len(xs) > 0:
            x = (xs[0] + xs[-1]) / 2.0
            points.append((x, y))

    # Require enough points to reliably fit a line.
    if len(points) < 5:
        return None, None, None, None

    points = np.asarray(points, dtype=np.float64)

    # Fit x = slope*y + intercept.
    slope, intercept = np.polyfit(
            points[:, 1],
            points[:, 0],
            1
        )

    # Calculate the line position near the bottom
    # of the image. This gives the rover a useful
    # estimate of where the line is approaching.
    y_ref = height * 0.75

    x_ref = slope * y_ref + intercept

    # Convert region-local coordinates to full-frame coordinates.
    x_ref += x_offset

    # Calculate offset relative to the camera center.
    center_x = full_width / 2.0

    offset_error = center_x - x_ref

    # Use the slope as the angle correction.
    angle_error = slope

    # Combine offset and angle into one CTE.
    error = offset_error + angle_weight * angle_error

    # Reject invalid calculations.
    if not np.isfinite(error):
        return None, None, None, None

    return error, (slope, intercept), offset_error, angle_error

def draw_fitted_line(line, x_offset, color, frame):

    if line is None:
        return

    # Get dimensions of the frame passed into this function
    height, width = frame.shape[:2]

    slope, intercept = line

    # Calculate the line's starting and ending x coordinates
    x1 = int(intercept + x_offset)

    x2 = int(
        slope * (height - 1) +
        intercept + x_offset
    )

    # Draw the fitted line on the frame
    cv2.line(
        frame,
        (x1, 0),
        (x2, height - 1),
        color,
        2
    )


# #def follow_line(sock):
#     vid = None
#     video_failures = 0
#     low_orange = np.array([0, 0, 20], dtype=np.uint8)
#     high_orange = np.array([70, 255, 255], dtype=np.uint8)
#     isAtFork = False
#     isAtShelf = False
#     fork_frames = 0
    
#     try:
#         while True:
#             # Recover the camera connection if needed.
#             if vid is None:
#                 vid = open_video(line_follow_url)

#                 if vid is None:
#                     print("Camera stream unavailable.")
#                     sock = send_command(sock, "STOP\n")
#                     time.sleep(RECONNECT_DELAY)
#                     continue

#             ret, frame = vid.read()

#             if not ret or frame is None:
#                 video_failures += 1
#                 print(
#                     f"Failed to read camera frame "
#                     f"({video_failures}/{MAX_VIDEO_FAILURES})."
#                 )

#                 # Do not keep driving on stale camera information.
#                 sock = send_command(sock, "STOP\n")

#                 if video_failures >= MAX_VIDEO_FAILURES:
#                     vid.release()
#                     vid = None
#                     video_failures = 0

#                 time.sleep(0.1)
#                 continue

#             video_failures = 0

#             # Blur the frame to reduce noise.
#             frame = cv2.GaussianBlur(frame, (5, 5), 0)

#             height, width = frame.shape[:2]

#             # Crop BEFORE detecting contours
#             crop_start = int(height * 0.15)
#             frame = frame[crop_start:height, :]

#             height, width = frame.shape[:2]

#             # Convert to HSV
#             hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

#             gray_threshold = cv2.inRange(
#                 hsv_frame,
#                 low_orange,
#                 high_orange
#             )

#             # Remove small isolated noise
#             open_kernel = np.ones((3, 3), np.uint8)

#             gray_threshold = cv2.morphologyEx(
#                 gray_threshold,
#                 cv2.MORPH_OPEN,
#                 open_kernel
#             )

#             # Connect nearby orange regions
#             close_kernel = np.ones((5, 5), np.uint8)

#             gray_threshold = cv2.morphologyEx(
#                 gray_threshold,
#                 cv2.MORPH_CLOSE,
#                 close_kernel
#             )

#             # Find contours
#             contours, _ = cv2.findContours(
#                 gray_threshold,
#                 cv2.RETR_EXTERNAL,
#                 cv2.CHAIN_APPROX_SIMPLE
#             )

#             # Filter contours by area
#             MIN_AREA = width * height * 0.001

#             valid_contours = [
#                 c for c in contours
#                 if cv2.contourArea(c) > MIN_AREA
#             ]

#             best_contour = None

#             if valid_contours:
#                 best_contour = max(
#                     valid_contours,
#                     key=cv2.contourArea
#                 )

#             height, width = frame.shape[:2]

#             center_x = width // 2
#             center_y = height // 2
#             # x, y, w, h = cv2.boundingRect(candidate)

#             # if w > width * 0.99:
#             #     print("CROSS FORK")
#             #     isAtFork = True
#             # else: print("Not fork")

#             error = None

#             #checkIfAtShelf()

#             if isAtShelf:
#                 sock = send_command(sock, f"{999}\n")
#                 break
#             elif isAtFork:
#                 sock = send_command(sock, f"{999}\n")
#                 break
#             if best_contour is not None:

#                 x, y, w, h = cv2.boundingRect(best_contour)

#                 area = cv2.contourArea(best_contour)

#                     # Check for a sufficiently wide and substantial contour
#                 if (
#                         w > width * 0.95
#                       and area > width * height * 0.005
#                 ):
#                     fork_frames += 1
#                     print("FORK?")
#                 else:
#                     fork_frames = 0

#                     # Require 3 consecutive frames
#                 if fork_frames >= 2:
#                         print("CROSS FORK")
#                         isAtFork = True
#                 elif fork_frames == 1: continue # dont reset after 1 frame seen
#                 else:
#                     fork_frames = 0
#                 # Fit a line to the detected tape.
#                 mask = np.zeros_like(gray_threshold)

#                 cv2.drawContours(
#                     mask, [best_contour], -1, 255, -1
#                 )

#                 points = []

#                 for y in range(height):
#                     xs = np.where(mask[y] > 0)[0]

#                     if len(xs) > 0:
#                         x = (xs[0] + xs[-1]) / 2.0
#                         points.append((x, y))

#                 # Need at least two points to fit a line.
#                 if len(points) >= 2:
#                     points = np.asarray(points, dtype=np.float64)

#                     slope, intercept = np.polyfit(
#                         points[:, 1],
#                         points[:, 0],
#                         1
#                     )

#                     # Offset error.
#                     y_ref = height / 2.0
#                     x_ref = y_ref * slope + intercept
#                     offset_error = center_x - x_ref

#                     #if angle_error  <= (abs(old_angle_error) + .1) and angle_error  >= (abs(old_angle_error) - .1): 
#                     # Angle error.
#                     angle_error = slope
#                     old_angle_error = angle_error

#                     # Combined error.
#                     error = (
#                         offset_error
#                         + angle_weight * angle_error
#                     )

#                     if not np.isfinite(error):
#                         error = None

#                     if error is not None:
#                         cv2.putText(
#                             frame, "Line: FOUND", (0, 20),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.5,
#                             (0, 255, 0), 2
#                         )

#                         cv2.drawContours(
#                             frame, [best_contour], -1,
#                             (0, 255, 0), 2
#                         )

#                         x1 = int(intercept)
#                         x2 = int((height - 1) * slope + intercept)

#                         cv2.line(
#                             frame, (x1, 0), (x2, height - 1),
#                             (255, 0, 255), 2
#                         )

#                         cv2.putText(
#                             frame,
#                             f"Offset: {offset_error:.1f} "
#                             f"Angle: {angle_error:.2f}",
#                             (0, 45), cv2.FONT_HERSHEY_SIMPLEX,
#                             0.5, (255, 255, 255), 1
#                         )

#                         cv2.putText(
#                             frame, f"Error: {error:.1f}", (0, 65),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.5,
#                             (255, 255, 255), 1
#                         )

#             # Send a fresh command every frame.
#             if error is not None:
#                 #if abs(error) > 55: error = -1
#                 sock = send_command(sock, f"{error:.3f}\n")
#             else:
#                 cv2.putText(
#                     frame, "Line: NOT FOUND", (0, 20),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.5,
#                     (0, 0, 255), 2
#                 )

#                 # Prevent the robot from following an old error.
#                 sock = send_command(sock, "STOP\n")

#             # Draw frame center and display output.
#             cv2.circle(
#                 frame, (center_x, center_y), 7,
#                 (255, 255, 255), -1
#             )

#             cv2.line(
#                 frame, (center_x, 0), (center_x, height - 1),
#                 (0, 255, 255), 2
#             )

#             cv2.imshow("Current Line-Following Output", frame)
#             cv2.imshow("Tape Mask", gray_threshold)


            
#             if cv2.waitKey(1) & 0xFF == ord("q"):
#                 break
    
#     # Dont exit program after finding cross
#     # except KeyboardInterrupt:
#     #     print("Program interrupted.")

#     except Exception as e:
#          print(f"Unexpected error: {e}")
#          sock = send_command(sock, "999\n")

#     finally:
#         sock = send_command(sock, "999\n")
#         print("Exiting follow_Line")
#     #     # Best-effort stop without entering another reconnect loop.
       
#     #     sock = send_command(sock, "STOP\n")

#     #     try:
#     #         sock.close()
#     #     except OSError:
#     #         pass

#     #     if vid is not None:
#     #         vid.release()

#     #     cv2.destroyAllWindows()
#     #     print("Line-following program stopped.")

def checkIfAtShelf():
    return False