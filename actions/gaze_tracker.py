"""
actions/gaze_tracker.py - Biomimetic Gaze Engine v4.1
- Rock-solid vertical eye tracking using skull-anchored eye corners
- 3-tier adaptive deadband (kills vibration completely)
- Corrected head pitch orientation and heavy neck damping
"""

import cv2
import mediapipe as mp
import numpy as np


class GazeEstimator:
    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473

    # Rigid eye corners (canthi) anchored to facial bones
    LEFT_EYE_INNER = 133
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_INNER = 362
    RIGHT_EYE_OUTER = 263

    NOSE_TIP = 1

    def __init__(self, min_detection_confidence=0.6, min_tracking_confidence=0.6):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def _get_eye_ratio(self, iris_pt, inner_pt, outer_pt):
        # 1. Horizontal Gaze: relative to inner & outer corners
        eye_width = abs(outer_pt[0] - inner_pt[0])
        if eye_width == 0:
            return 0.0, 0.0

        eye_center_x = (inner_pt[0] + outer_pt[0]) / 2.0
        norm_x = (iris_pt[0] - eye_center_x) / (eye_width * 0.45)

        # 2. Vertical Gaze: relative to the stable corner-to-corner baseline
        # (This bypasses eyelid fluttering and accurately tracks UP and DOWN)
        corner_baseline_y = (inner_pt[1] + outer_pt[1]) / 2.0
        # Positive = looking down, Negative = looking up
        norm_y = (iris_pt[1] - corner_baseline_y + (eye_width * 0.08)) / (eye_width * 0.22)

        norm_x = float(np.clip(norm_x, -1.0, 1.0))
        norm_y = float(np.clip(norm_y, -1.0, 1.0))

        return norm_x, norm_y

    def estimate(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return {"detected": False, "eye_x": 0.0, "eye_y": 0.0, "head_x": 0.0, "head_y": 0.0}

        mesh = results.multi_face_landmarks[0].landmark

        def to_px(lm):
            return np.array([lm.x * w, lm.y * h])

        left_iris = to_px(mesh[self.LEFT_IRIS_CENTER])
        right_iris = to_px(mesh[self.RIGHT_IRIS_CENTER])

        l_in, l_out = to_px(mesh[self.LEFT_EYE_INNER]), to_px(mesh[self.LEFT_EYE_OUTER])
        r_in, r_out = to_px(mesh[self.RIGHT_EYE_INNER]), to_px(mesh[self.RIGHT_EYE_OUTER])

        lx, ly = self._get_eye_ratio(left_iris, l_in, l_out)
        rx, ry = self._get_eye_ratio(right_iris, r_in, r_out)

        avg_eye_x = (lx + rx) / 2.0
        avg_eye_y = (ly + ry) / 2.0

        # Head Orientation from nose position
        nose = to_px(mesh[self.NOSE_TIP])
        head_x = float(np.clip((nose[0] - (w / 2.0)) / (w / 3.0), -1.0, 1.0))
        # Head pitch: Down is positive, Up is negative
        head_y = float(np.clip((nose[1] - (h / 2.0)) / (h / 3.0), -1.0, 1.0))

        return {
            "detected": True,
            "eye_x": round(avg_eye_x, 3),
            "eye_y": round(avg_eye_y, 3),
            "head_x": round(head_x, 3),
            "head_y": round(head_y, 3)
        }

    def release(self):
        self.face_mesh.close()


class GazeKinematics:
    """
    3-Tier Biological Filter:
    - Tier 1 (Noise Floor < 0.035): Zero movement (kills vibration completely).
    - Tier 2 (Smooth Drift 0.035 - 0.09): Slow, calm adjustment.
    - Tier 3 (Saccade > 0.09): Fast human glance snap.
    """
    def __init__(self):
        self.smooth_eye_x = 0.0
        self.smooth_eye_y = 0.0
        self.smooth_head_x = 0.0
        self.smooth_head_y = 0.0

    def update(self, raw):
        if not raw["detected"]:
            # Drift gently to neutral center
            self.smooth_eye_x += (0.0 - self.smooth_eye_x) * 0.04
            self.smooth_eye_y += (0.0 - self.smooth_eye_y) * 0.04
            self.smooth_head_x += (0.0 - self.smooth_head_x) * 0.02
            self.smooth_head_y += (0.0 - self.smooth_head_y) * 0.02
            return {
                "detected": False,
                "eye_x": round(self.smooth_eye_x, 3),
                "eye_y": round(self.smooth_eye_y, 3),
                "head_x": round(self.smooth_head_x, 3),
                "head_y": round(self.smooth_head_y, 3)
            }

        delta_x = raw["eye_x"] - self.smooth_eye_x
        delta_y = raw["eye_y"] - self.smooth_eye_y
        dist = np.hypot(delta_x, delta_y)

        # 1. EYE FILTER (Anti-Vibration)
        if dist < 0.035:
            # Noise threshold: do nothing, eyeball stays rock solid
            pass
        elif dist < 0.09:
            # Smooth subtle adjustment
            self.smooth_eye_x += delta_x * 0.20
            self.smooth_eye_y += delta_y * 0.20
        else:
            # Rapid biological saccade
            self.smooth_eye_x += delta_x * 0.70
            self.smooth_eye_y += delta_y * 0.70

        # 2. BALANCED NECK INERTIA (Responsive follow without sluggish lag)
        self.smooth_head_x += (raw["head_x"] - self.smooth_head_x) * 0.14
        self.smooth_head_y += (raw["head_y"] - self.smooth_head_y) * 0.14

        return {
            "detected": True,
            "eye_x": round(self.smooth_eye_x, 3),
            "eye_y": round(self.smooth_eye_y, 3),
            "head_x": round(self.smooth_head_x, 3),
            "head_y": round(self.smooth_head_y, 3)
        }