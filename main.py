from face_recognition_system import FaceRecognition

if __name__ == "__main__":
    face_system = FaceRecognition()

    # To add a new person:
    image_paths = []
    image_paths1 = []
    face_system.add_new_person("Joseph", image_paths)
    face_system.add_new_person("Atigo", image_paths1)

    # Start recognition
    face_system.start_recognition()