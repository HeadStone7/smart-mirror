import os
import shutil

import cv2


def create_directory_if_not_exists(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")


def copy_image_to_directory(image_path: str, target_dir: str):
    try:
        filename = os.path.basename(image_path)
        new_path = os.path.join(target_dir, filename)
        shutil.copy2(image_path, new_path)
        return new_path
    except Exception as e:
        print(f"Error copying {image_path}: {str(e)}")
        return None


def _draw_face_annotations(frame, top, right, bottom, left, display_text):
    """Draw stable bounding box and text for detected faces"""
    # Calculate box thickness based on frame size
    thickness = max(1, min(2, int(frame.shape[1] / 640)))

    # Draw anti-aliased rectangle around the face
    cv2.rectangle(
        frame,
        (left, top),
        (right, bottom),
        (0, 255, 0),
        thickness,
        cv2.LINE_AA
    )

    # Calculate text background rectangle size
    text_size = cv2.getTextSize(
        display_text,
        cv2.FONT_HERSHEY_DUPLEX,
        0.6,
        1
    )[0]

    # Draw semi-transparent background for text
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (left, bottom - 35),
        (right, bottom),
        (0, 255, 0),
        cv2.FILLED
    )
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Add name text with anti-aliasing
    cv2.putText(
        frame,
        display_text,
        (left + 6, bottom - 6),
        cv2.FONT_HERSHEY_DUPLEX,
        0.6,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )
