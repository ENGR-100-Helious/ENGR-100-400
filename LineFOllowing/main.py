from pupil_apriltags import Detector
from projectFunctions import *
import cv2
import socket
import numpy as np
import time

APRIL_TAG_IP = "192.168.50.213"
LINE_FOLLOW_IP = "192.168.50.214"
TCP_PORT = 5005
april_tag_url = f"http://{APRIL_TAG_IP}/stream"
line_follow_url = f"http://{LINE_FOLLOW_IP}/stream"

CONNECT_TIMEOUT = 3
SEND_TIMEOUT = 2
RECONNECT_DELAY = 1
MAX_VIDEO_FAILURES = 5

isAtFork = False
isAtShelf = False
angle_weight = 10

# def follow_line(sock):
#     vid = None
#     video_failures = 0
#     angle_weight = 10
#     low_orange = np.array([0, 0, 15], dtype=np.uint8)
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
#                       and area > width * height * 0.4
#                 ):
#                     fork_frames += 1
#                     print("FORK?")
#                 else:
#                     fork_frames = 0

#                     # Require 3 consecutive frames
#                 if fork_frames >= 15:
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

# Assumed to already exist elsewhere in your project:
#   open_video, send_command, detect_line_in_region, draw_fitted_line,
#   line_follow_url, RECONNECT_DELAY, MAX_VIDEO_FAILURES

# ----------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------
LOW_ORANGE = np.array([0, 0, 15], dtype=np.uint8)    # V=15 matches your older version
HIGH_ORANGE = np.array([70, 255, 255], dtype=np.uint8)

ANGLE_WEIGHT = 10            # weight of the line-slope term in the steering error

FORK_CONFIRM_FRAMES = 2      # consecutive frames needed to confirm a fork
FORK_WIDTH_FRAC = 0.95       # contour must span this fraction of the width
FORK_MIN_AREA_FRAC = 0.005   # ignore contours smaller than this fraction of the frame

CENTER_TOLERANCE = 0.1       # |middle error| below this counts as centered (tune to your units)
CENTER_CONFIRM_FRAMES = 3    # consecutive centered frames needed to finish a turn
TURN_TIMEOUT = 10.0          # seconds before turn_to_branch gives up


# ----------------------------------------------------------------------
# Camera wrapper (keeps the stream open across both functions)
# ----------------------------------------------------------------------
class Camera:
    def __init__(self, url):
        self.url = url
        self.vid = None
        self.failures = 0

    def read(self, sock):
        """Returns (sock, frame). frame is None if no usable frame this call."""
        if self.vid is None:
            self.vid = open_video(self.url)
            if self.vid is None:
                print("Camera stream unavailable.")
                sock = send_command(sock, "STOP\n")
                time.sleep(RECONNECT_DELAY)
                return sock, None

        ret, frame = self.vid.read()

        if not ret or frame is None:
            self.failures += 1
            print(f"Failed to read camera frame ({self.failures}/{MAX_VIDEO_FAILURES}).")

            # Stop rather than following an old camera frame.
            sock = send_command(sock, "STOP\n")

            if self.failures >= MAX_VIDEO_FAILURES:
                self.release()
            time.sleep(0.1)
            return sock, None

        self.failures = 0
        return sock, frame

    def flush(self, n=5):
        """Discard buffered frames so we don't steer on stale images after a pause."""
        if self.vid is not None:
            for _ in range(n):
                self.vid.grab()

    def release(self):
        if self.vid is not None:
            self.vid.release()
        self.vid = None
        self.failures = 0


# ----------------------------------------------------------------------
# Full-frame steering error (same math as your original contour fit)
# ----------------------------------------------------------------------
def full_frame_error(mask, width, height):
    """
    Fits a line through the largest orange contour in the whole frame and
    returns offset_error + ANGLE_WEIGHT * slope, or None if no line is found.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = width * height * 0.001
    valid = [c for c in contours if cv2.contourArea(c) > min_area]
    if not valid:
        return None, None

    best = max(valid, key=cv2.contourArea)

    line_mask = np.zeros_like(mask)
    cv2.drawContours(line_mask, [best], -1, 255, -1)

    # Midpoint of the tape on each row.
    points = []
    for row in range(height):
        xs = np.where(line_mask[row] > 0)[0]
        if len(xs) > 0:
            points.append(((xs[0] + xs[-1]) / 2.0, row))

    if len(points) < 2:
        return None, best

    pts = np.asarray(points, dtype=np.float64)
    slope, intercept = np.polyfit(pts[:, 1], pts[:, 0], 1)

    # Offset measured at the vertical center of the frame.
    x_ref = (height / 2.0) * slope + intercept
    offset_error = (width // 2) - x_ref

    error = offset_error + ANGLE_WEIGHT * slope
    if not np.isfinite(error):
        return None, best

    return float(error), best


# ----------------------------------------------------------------------
# Shared vision processing
# ----------------------------------------------------------------------
def analyze_frame(frame):
    """Preprocess a frame and compute the fork flag, full-frame error, and region errors."""
    frame = cv2.GaussianBlur(frame, (5, 5), 0)

    # Crop the top 15% of the image.
    height, width = frame.shape[:2]
    frame = frame[int(height * 0.15):height, :]
    height, width = frame.shape[:2]

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_ORANGE, HIGH_ORANGE)

    # Remove isolated noise, then connect nearby orange pixels.
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    # Steering error from the whole frame (this is what follow_line uses).
    full_error, best_contour = full_frame_error(mask, width, height)

    # Fork detection: a big contour spanning nearly the full width.
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_fork_area = width * height * FORK_MIN_AREA_FRAC
    wide_fork = False
    for contour in contours:
        if cv2.contourArea(contour) < min_fork_area:
            continue
        _, _, w, _ = cv2.boundingRect(contour)
        if w > width * FORK_WIDTH_FRAC:
            wide_fork = True
            break

    # Three vertical regions, each with its own line error (used for branch turning).
    third = width // 3
    regions = {
        "left":   (mask[:, :third], 0),
        "middle": (mask[:, third:third * 2], third),
        "right":  (mask[:, third * 2:], third * 2),
    }

    errors, lines = {}, {}
    for name, (region_mask, x_offset) in regions.items():
        error, line, _offset, _angle = detect_line_in_region(region_mask, x_offset, width)
        errors[name] = error
        lines[name] = (line, x_offset)

    print(
        f"FULL: {full_error} | LEFT: {errors['left']} | "
        f"MIDDLE: {errors['middle']} | RIGHT: {errors['right']}"
    )

    return {
        "frame": frame,
        "mask": mask,
        "width": width,
        "height": height,
        "third": third,
        "wide_fork": wide_fork,
        "full_error": full_error,
        "best_contour": best_contour,
        "errors": errors,
        "lines": lines,
    }


def detect_shelf(analysis):
    """Placeholder: return True when your shelf marker is detected."""
    return False


def show_debug(analysis, status=None):
    """Draw boundaries, fitted lines, errors, and show the windows. Returns True if Q pressed."""
    frame = analysis["frame"]
    height, width, third = analysis["height"], analysis["width"], analysis["third"]
    errors = analysis["errors"]

    for x in (third, third * 2):
        cv2.line(frame, (x, 0), (x, height - 1), (255, 0, 0), 2)

    colors = {"left": (255, 0, 255), "middle": (0, 255, 0), "right": (0, 255, 255)}
    labels = {"left": "L", "middle": "M", "right": "R"}

    for i, name in enumerate(("left", "middle", "right")):
        line, x_offset = analysis["lines"][name]
        draw_fitted_line(line, x_offset, colors[name], frame)

        err = errors[name]
        cv2.putText(
            frame, f"{labels[name]}: {err if err is not None else 'None'}",
            (5, 20 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45, colors[name], 1
        )

    full_error = analysis["full_error"]
    cv2.putText(
        frame, f"FULL: {full_error:.1f}" if full_error is not None else "FULL: None",
        (5, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1
    )

    if analysis["best_contour"] is not None:
        cv2.drawContours(frame, [analysis["best_contour"]], -1, (0, 255, 0), 1)

    if status:
        cv2.putText(frame, status, (5, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.circle(frame, (width // 2, height // 2), 7, (255, 255, 255), -1)

    cv2.imshow("Current Line-Following Output", frame)
    cv2.imshow("Tape Mask", analysis["mask"])

    return (cv2.waitKey(1) & 0xFF) == ord("q")


# ----------------------------------------------------------------------
# Function 1: follow the line until a fork or shelf
# ----------------------------------------------------------------------
def follow_line(sock, cam):
    """
    Steers on the full-frame error (offset + angle) until a fork or shelf is detected.
    Returns (sock, result) where result is "fork", "shelf", or "quit".
    """
    cam.flush()
    fork_frames = 0

    while True:
        sock, frame = cam.read(sock)
        if frame is None:
            continue

        a = analyze_frame(frame)

        # Require several consecutive frames to avoid false forks.
        if a["wide_fork"]:
            fork_frames += 1
            print(f"Possible fork: {fork_frames}")
        else:
            fork_frames = 0

        if fork_frames >= FORK_CONFIRM_FRAMES:
            print("Fork detected. Stopping.")
            sock = send_command(sock, "999\n")
            show_debug(a, "FORK DETECTED - STOPPED")
            return sock, "fork"

        if detect_shelf(a):
            print("Shelf detected. Stopping.")
            sock = send_command(sock, "999\n")
            show_debug(a, "SHELF DETECTED - STOPPED")
            return sock, "shelf"

        # Normal following: full-frame error.
        error = a["full_error"]
        if error is not None:
            sock = send_command(sock, f"{error:.3f}\n")
        else:
            sock = send_command(sock, "STOP\n")

        if show_debug(a):
            return sock, "quit"


# ----------------------------------------------------------------------
# Function 2: steer on a chosen region's error until it's centered
# ----------------------------------------------------------------------
def turn_to_branch(sock, cam, branch):
    """
    branch: "left", "right", or "middle".
    Steers using that region's error until the middle region holds the line with a
    small error and the wide fork bar is gone, for CENTER_CONFIRM_FRAMES frames in a row.
    Returns (sock, result) where result is "centered", "timeout", or "quit".
    """
    if branch not in ("left", "right", "middle"):
        raise ValueError(f"branch must be 'left', 'right', or 'middle', got {branch!r}")

    cam.flush()
    centered_frames = 0
    start = time.time()

    while True:
        if time.time() - start > TURN_TIMEOUT:
            print("Turn timed out.")
            sock = send_command(sock, "STOP\n")
            return sock, "timeout"

        sock, frame = cam.read(sock)
        if frame is None:
            continue

        a = analyze_frame(frame)

        # Drive using the chosen branch's error.
        error = a["errors"][branch]
        if error is not None:
            sock = send_command(sock, f"{error:.3f}\n")
        else:
            sock = send_command(sock, "STOP\n")

        middle_error = a["errors"]["middle"]
        is_centered = (
            middle_error is not None
            and abs(middle_error) < CENTER_TOLERANCE
            and not a["wide_fork"]
        )
        centered_frames = centered_frames + 1 if is_centered else 0

        if show_debug(a, f"TURNING {branch.upper()} ({centered_frames}/{CENTER_CONFIRM_FRAMES})"):
            return sock, "quit"

        if centered_frames >= CENTER_CONFIRM_FRAMES:
            print("Branch centered.")
            return sock, "centered"




def main():   
    detector = Detector(
    families="tag36h11",
    nthreads=1,
    quad_decimate=1.0,
    quad_sigma=0.0,
    refine_edges=1,
    decode_sharpening=0.25,
    debug=0)

    time.sleep(2)
    sock = socket_setup()

    line_follow_camera = Camera(line_follow_url)
    try:
       
        sock, result = follow_line(sock, line_follow_camera)
            

        if result == "fork":
            sock, result = turn_to_branch(sock, line_follow_camera, "left")  # pick your branch
        #     if result == "centered":
        #         sock, result = follow_line(sock, line_follow_camera)

    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        sock = send_command(sock, "999\n")
        line_follow_camera.release()
        cv2.destroyAllWindows()
        print("Exiting Program")


    #cap = cv2.VideoCapture(april_tag_url)
    #print("Camera opened:", cap.isOpened())
    #frame = cv2.imread("straight line fork.png")
    #isAtFork = False;
    #follow_line(sock);
    #getAprilTagIDs(detector,frame)
    #time.sleep(5)
    #follow_line(sock)


    
    # robot arm pick up sequence
    # check for intersection
    # follow line until and the intersect

    # check for if at intersection find april tag ids
    #getAprilTagIDs(detector,frame)

    # take the correct path
    # follow line until distance sensor detects shelf
    # Place object with robot arm    
    # Backup on line until cross
    # go to pick up location
    # repeat
                
    # except KeyboardInterrupt:
    #     print("Program interrupted.")
                
    # except Exception as e:
    #     print(f"Unexpected error: {e}")
    # except OSError:
    #         pass
                               
    #sock.close()
    #cap.release()
    #cv2.destroyAllWindows()
                
    print("Program Stopped")

if __name__ == "__main__":
    main()
