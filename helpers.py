import base64
import io
import numpy as np
from PIL import Image
import pickle
import os

# Try to import face_recognition, otherwise fallback
try:
    import face_recognition
    HAVE_FR = True
except Exception:
    HAVE_FR = False
    import cv2

def decode_base64_image(data_url):
    # data_url expected like "data:image/png;base64,...."
    header, encoded = data_url.split(",", 1)
    img_data = base64.b64decode(encoded)
    return Image.open(io.BytesIO(img_data))

def image_to_numpy(pil_image):
    return np.array(pil_image.convert('RGB'))

def get_face_encoding_from_pil(pil_image):
    img = image_to_numpy(pil_image)
    if HAVE_FR:
        encs = face_recognition.face_encodings(img)
        return encs[0] if encs else None
    else:
        # fallback: return simple downscaled histogram as a placeholder (NOT REAL RECOGNITION)
        import cv2
        img_small = cv2.resize(img, (64,64))
        hist = cv2.calcHist([img_small], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist

def compare_encodings(enc1, enc2, threshold=0.6):
    import numpy as np
    if enc1 is None or enc2 is None:
        return False
    if HAVE_FR:
        dist = np.linalg.norm(enc1 - enc2)
        return dist <= threshold
    else:
        # cosine similarity fallback
        num = np.dot(enc1, enc2)
        den = np.linalg.norm(enc1) * np.linalg.norm(enc2)
        sim = num / den if den != 0 else 0
        return sim > 0.85

def serialize_encoding(enc):
    # use pickle bytes
    return pickle.dumps(enc)

def deserialize_encoding(b):
    return pickle.loads(b) if b else None