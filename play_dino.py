import os
import time
from typing import Dict, Optional, Tuple

import cv2
import pyautogui
from ultralytics import YOLO

MODEL_FILE = "best.pt"
WINDOW_NAME = "Dino Control Camera - Low Latency"

# Giảm overhead tối đa khi gửi phím
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# ======================
# Tinh chỉnh phản hồi nhanh
# ======================
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
INFER_SIZE = 416            # nhỏ hơn để tăng FPS / giảm latency
CONFIDENCE_THRESHOLD = 0.22 # nhạy hơn bản cũ
IOU_THRESHOLD = 0.45
MAX_DET = 1                 # chỉ lấy detection mạnh nhất
MIN_BOX_AREA = 1400         # vẫn lọc box nhỏ để tránh nhiễu
ROI_RATIO = 0.72            # chỉ nhìn vùng giữa ảnh để giảm nhiễu nền
SCORE_DECAY = 0.72          # độ nhớ theo frame
IMMEDIATE_CONF = 0.78       # conf cao thì phản ứng tức thì
PAPER_TRIGGER = 0.95        # ngưỡng kích hoạt nhảy
PAPER_RELEASE = 0.35        # phải thả tay/đổi cử chỉ xuống dưới ngưỡng này mới nhảy tiếp
ROCK_TRIGGER = 0.82         # ngưỡng giữ cúi
ROCK_RELEASE = 0.38
SCISSORS_CANCEL = 0.90      # kéo = neutral/cancel mạnh
JUMP_COOLDOWN = 0.11        # thấp nhưng không quá spam
HUD_ALPHA = 0.82


class GestureState:
    def __init__(self) -> None:
        self.scores: Dict[str, float] = {"paper": 0.0, "rock": 0.0, "scissors": 0.0}
        self.last_jump_time = 0.0
        self.paper_armed = True
        self.is_ducking = False
        self.last_label: Optional[str] = None
        self.last_conf = 0.0
        self.last_latency_ms = 0.0
        self.last_fps = 0.0


def load_model() -> YOLO:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, MODEL_FILE)
    return YOLO(model_path)


def init_camera(index: int = CAMERA_INDEX) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 60)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    try:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    except Exception:
        pass
    return cap


def get_roi(frame):
    h, w = frame.shape[:2]
    roi_w = int(w * ROI_RATIO)
    roi_h = int(h * ROI_RATIO)
    x1 = (w - roi_w) // 2
    y1 = (h - roi_h) // 2
    x2 = x1 + roi_w
    y2 = y1 + roi_h
    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)


def get_best_detection(results, model_names) -> Optional[Tuple[int, int, int, int, str, float, int]]:
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None

    best = None
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0].item())
        cls_id = int(box.cls[0].item())
        class_name = str(model_names[cls_id]).lower()
        area = max(0, x2 - x1) * max(0, y2 - y1)

        if area < MIN_BOX_AREA:
            continue
        if best is None or conf > best[5] or (conf == best[5] and area > best[6]):
            best = (x1, y1, x2, y2, class_name, conf, area)

    return best


def decay_scores(state: GestureState) -> None:
    for key in state.scores:
        state.scores[key] *= SCORE_DECAY
        if state.scores[key] < 0.01:
            state.scores[key] = 0.0


def update_scores(state: GestureState, label: Optional[str], conf: float) -> None:
    decay_scores(state)
    if label in state.scores:
        # cộng dồn điểm theo conf để vừa nhạy vừa chống rung
        state.scores[label] = min(1.6, state.scores[label] + conf)

        # detection rất chắc thì đẩy điểm lên ngưỡng kích hoạt gần như ngay lập tức
        if conf >= IMMEDIATE_CONF:
            if label == "paper":
                state.scores["paper"] = max(state.scores["paper"], PAPER_TRIGGER + 0.08)
            elif label == "rock":
                state.scores["rock"] = max(state.scores["rock"], ROCK_TRIGGER + 0.08)
            elif label == "scissors":
                state.scores["scissors"] = max(state.scores["scissors"], SCISSORS_CANCEL + 0.08)


def handle_controls(state: GestureState, now: float) -> None:
    paper_score = state.scores["paper"]
    rock_score = state.scores["rock"]
    scissors_score = state.scores["scissors"]

    # kéo = neutral/cancel để dừng cúi và khóa nhảy ngoài ý muốn
    if scissors_score >= SCISSORS_CANCEL:
        if state.is_ducking:
            pyautogui.keyUp("down")
            state.is_ducking = False
        state.paper_armed = True
        return

    # Rock ưu tiên giữ cúi theo trạng thái
    if rock_score >= ROCK_TRIGGER and rock_score > paper_score:
        if not state.is_ducking:
            pyautogui.keyDown("down")
            state.is_ducking = True
    elif state.is_ducking and rock_score <= ROCK_RELEASE:
        pyautogui.keyUp("down")
        state.is_ducking = False

    # Paper kích hoạt theo rising edge, gần giống bấm phím thật hơn là spam liên tục
    jump_ready = (now - state.last_jump_time) >= JUMP_COOLDOWN
    if paper_score <= PAPER_RELEASE:
        state.paper_armed = True

    if (
        paper_score >= PAPER_TRIGGER
        and state.paper_armed
        and jump_ready
        and not state.is_ducking
        and paper_score >= rock_score
    ):
        pyautogui.press("space")
        state.last_jump_time = now
        state.paper_armed = False


def draw_overlay(frame, roi_rect, det, state: GestureState):
    x1, y1, x2, y2 = roi_rect
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (80, 180, 255), 2)

    if det is not None:
        dx1, dy1, dx2, dy2, label, conf, area = det
        dx1 += x1
        dx2 += x1
        dy1 += y1
        dy2 += y1
        cv2.rectangle(overlay, (dx1, dy1), (dx2, dy2), (0, 255, 0), 2)
        cv2.putText(
            overlay,
            f"{label} {conf:.2f}",
            (dx1, max(24, dy1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    hud_lines = [
        f"paper:{state.scores['paper']:.2f} rock:{state.scores['rock']:.2f} scissors:{state.scores['scissors']:.2f}",
        f"duck:{'ON' if state.is_ducking else 'OFF'}  armed:{'YES' if state.paper_armed else 'NO'}",
        f"fps:{state.last_fps:.1f}  loop:{state.last_latency_ms:.1f}ms",
        "Paper=Jump | Rock=Hold Duck | Scissors=Cancel | q=Quit",
    ]

    panel_h = 112
    cv2.rectangle(overlay, (8, 8), (635, 8 + panel_h), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, HUD_ALPHA, frame, 1 - HUD_ALPHA, 0)

    for i, line in enumerate(hud_lines):
        cv2.putText(
            frame,
            line,
            (18, 34 + i * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (255, 255, 255) if i < 3 else (0, 255, 255),
            2,
        )
    return frame


def main():
    try:
        model = load_model()
        print("Đã tải mô hình YOLOv8 thành công.")
    except Exception as e:
        print(f"Lỗi tải mô hình: {e}")
        return

    cap = init_camera(CAMERA_INDEX)
    if not cap.isOpened():
        print("Không thể mở webcam.")
        return

    # Warm-up để giảm độ trễ vài frame đầu
    try:
        import numpy as np
        dummy = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        model.predict(dummy, imgsz=INFER_SIZE, conf=CONFIDENCE_THRESHOLD, iou=IOU_THRESHOLD, max_det=MAX_DET, verbose=False)
    except Exception:
        pass

    state = GestureState()
    prev_loop_time = time.perf_counter()

    print("\n--- LOW LATENCY MODE ---")
    print("- Paper    : Nhảy rất nhanh theo rising edge")
    print("- Rock     : Giữ cúi theo trạng thái cử chỉ")
    print("- Scissors : Hủy lệnh / neutral")
    print("- q        : Thoát")
    print("Mẹo: đặt tay trong khung ROI màu xanh để phản hồi nhanh và ổn định hơn.\n")

    try:
        while True:
            loop_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                print("Mất tín hiệu webcam.")
                break

            frame = cv2.flip(frame, 1)
            roi, roi_rect = get_roi(frame)

            results = model.predict(
                source=roi,
                imgsz=INFER_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                iou=IOU_THRESHOLD,
                max_det=MAX_DET,
                verbose=False,
            )
            best = get_best_detection(results, model.names)

            label = None
            conf = 0.0
            if best is not None:
                label = best[4]
                conf = best[5]

            now = time.perf_counter()
            update_scores(state, label, conf)
            handle_controls(state, now)

            loop_end = time.perf_counter()
            dt = max(1e-6, loop_end - prev_loop_time)
            state.last_fps = 1.0 / dt
            state.last_latency_ms = (loop_end - loop_start) * 1000.0
            state.last_label = label
            state.last_conf = conf
            prev_loop_time = loop_end

            display = draw_overlay(frame, roi_rect, best, state)
            cv2.imshow(WINDOW_NAME, display)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        if state.is_ducking:
            pyautogui.keyUp("down")
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
