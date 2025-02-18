import face_recognition
import cv2
import numpy as np
from collections import defaultdict
import shutil
import pyttsx3
from datetime import datetime
import logging
import threading
import queue
import json
from pathlib import Path
from typing import List
from utils import _draw_face_annotations


class FaceRecognition:
    def __init__(self,
                 known_faces_dir: str = "known_faces",
                 log_dir: str = "logs",
                 min_face_size: int = 20,
                 recognition_threshold: float = 0.6):
        """
        Initialize the face recognition system with improved configuration.

        Args:
            known_faces_dir: Directory for storing known face images
            log_dir: Directory for storing logs
            min_face_size: Minimum face size to detect (in pixels)
            recognition_threshold: Threshold for face recognition confidence
        """
        self.known_faces_dir = Path(known_faces_dir)
        self.log_dir = Path(log_dir)
        self.min_face_size = min_face_size
        self.recognition_threshold = recognition_threshold

        # Initialize storage
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_encodings_dict = defaultdict(list)
        self.last_recognition_time = defaultdict(float)

        # Set up voice engine in a separate thread
        self.voice_queue = queue.Queue()
        self.engine = pyttsx3.init()
        self.setup_voice_engine()

        # Set up logging
        self._setup_logging()

        # Load known faces
        self.load_known_faces()

        # Start voice processing thread
        self.voice_thread = threading.Thread(target=self._process_voice_queue, daemon=True)
        self.voice_thread.start()

    def _setup_logging(self):
        """Configure logging system"""
        self.log_dir.mkdir(exist_ok=True)
        log_file = self.log_dir / f"face_recognition_{datetime.now():%Y%m%d}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_voice_engine(self):
        """Configure text-to-speech engine with optimal settings"""
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)  # Female voice
        self.engine.setProperty('rate', 150)  # Slightly faster than default
        self.engine.setProperty('volume', 0.8)  # 80% volume

    def _process_voice_queue(self):
        """Process voice messages in a separate thread"""
        while True:
            try:
                message = self.voice_queue.get()
                self.engine.say(message)
                self.engine.runAndWait()
                self.voice_queue.task_done()
            except Exception as e:
                self.logger.error(f"Voice processing error: {e}")

    def load_known_faces(self):
        """Load known faces with improved error handling and validation"""
        self.known_faces_dir.mkdir(exist_ok=True)
        self.logger.info(f"Loading known faces from {self.known_faces_dir}")

        for person_dir in self.known_faces_dir.iterdir():
            if not person_dir.is_dir():
                continue

            person_name = person_dir.name
            self.logger.info(f"Loading images for {person_name}...")

            for image_path in person_dir.glob("*.[jJ][pP][gG]"):
                self._process_and_add_face(image_path, person_name)

        self.logger.info(
            f"Loaded {len(self.known_face_names)} face encodings for {len(self.face_encodings_dict)} people")

    def _process_and_add_face(self, image_path: Path, person_name: str) -> bool:
        """Process and add a face with improved image processing"""
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                self.logger.error(f"Could not load {image_path}")
                return False

            # Resize large images to improve performance
            max_size = 1024
            height, width = image.shape[:2]
            if height > max_size or width > max_size:
                scale = max_size / max(height, width)
                image = cv2.resize(image, (int(width * scale), int(height * scale)))

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect faces with minimum size requirement
            face_locations = face_recognition.face_locations(
                rgb_image,
                model="cnn" if self._has_gpu() else "hog"
            )

            if not face_locations:
                self.logger.warning(f"No faces found in {image_path.name}")
                return False

            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

            if face_encodings:
                self.face_encodings_dict[person_name].extend(face_encodings)
                self.known_face_encodings.extend(face_encodings)
                self.known_face_names.extend([person_name] * len(face_encodings))
                self.logger.info(f"Added {len(face_encodings)} face(s) from {image_path.name}")
                return True

        except Exception as e:
            self.logger.error(f"Error processing {image_path}: {e}")

        return False

    def _has_gpu(self) -> bool:
        """Check if CUDA GPU is available"""
        return cv2.cuda.getCudaEnabledDeviceCount() > 0

    def add_new_person(self, person_name: str, image_paths: List[str]) -> int:
        """Add a new person with multiple images and validation"""
        person_dir = self.known_faces_dir / person_name
        person_dir.mkdir(exist_ok=True)

        successful_adds = 0

        for image_path in image_paths:
            try:
                source_path = Path(image_path)
                if not source_path.exists():
                    self.logger.error(f"Source image {image_path} does not exist")
                    continue

                new_path = person_dir / source_path.name
                shutil.copy2(source_path, new_path)

                if self._process_and_add_face(new_path, person_name):
                    successful_adds += 1

            except Exception as e:
                self.logger.error(f"Error adding {image_path}: {e}")

        return successful_adds

    def start_recognition(self, confidence_threshold: float = 0.6):
        """Start real-time face recognition with stable display"""
        video_capture = cv2.VideoCapture(0)

        if not video_capture.isOpened():
            self.logger.error("Could not access webcam")
            return

        self.logger.info("Starting face recognition... Press 'q' to quit")

        # Performance optimization variables
        frame_count = 0
        recognition_interval = 3  # Process every N frames

        # Store previous detections to reduce flickering
        prev_faces = []
        smoothing_frames = 5  # Number of frames to smooth over

        while True:
            ret, frame = video_capture.read()
            if not ret:
                continue

            frame_count += 1
            current_faces = []

            # Process face detection every N frames
            if frame_count % recognition_interval == 0:
                # Resize frame for faster processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(
                    rgb_small_frame,
                    model="cnn" if self._has_gpu() else "hog"
                )
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                # Process each face
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # Scale back up face locations
                    top *= 2
                    right *= 2
                    bottom *= 2
                    left *= 2

                    matches = face_recognition.compare_faces(
                        self.known_face_encodings,
                        face_encoding,
                        tolerance=self.recognition_threshold
                    )
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)

                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        confidence = (1 - face_distances[best_match_index]) * 100

                        if matches[best_match_index] and confidence >= confidence_threshold * 100:
                            name = self.known_face_names[best_match_index]

                            # Throttle voice announcements
                            current_time = datetime.now().timestamp()
                            if current_time - self.last_recognition_time[name] > 5.0:
                                self.voice_queue.put(f"Hello {name}")
                                self.last_recognition_time[name] = current_time

                            display_text = f"{name} ({confidence:.1f}%)"
                        else:
                            display_text = "Unknown"
                    else:
                        display_text = "Unknown"

                    current_faces.append({
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left,
                        'display_text': display_text
                    })

                # Update previous faces buffer
                prev_faces.append(current_faces)
                if len(prev_faces) > smoothing_frames:
                    prev_faces.pop(0)

            # Draw annotations using smoothed positions
            if prev_faces:
                # Use the most recent face detections
                latest_faces = prev_faces[-1]

                for face in latest_faces:
                    _draw_face_annotations(
                        frame,
                        face['top'],
                        face['right'],
                        face['bottom'],
                        face['left'],
                        face['display_text']
                    )

            cv2.imshow('Face Recognition', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        cv2.destroyAllWindows()

    def save_known_faces(self):
        """Save the current state of known faces to disk"""
        data = {
            name: [encoding.tolist() for encoding in encodings]
            for name, encodings in self.face_encodings_dict.items()
        }

        with open(self.known_faces_dir / 'face_encodings.json', 'w') as f:
            json.dump(data, f)