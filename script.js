const video = document.getElementById('video');
const canvas = document.getElementById('overlay');
const statusText = document.getElementById('status');
let faceMatcher;
const recognizedStudents = new Set();

// Attendance tracking (optional local)
let students = [
  { student_id: 'S101', name: 'atiksh', present: 0, absent: 0 },
  { student_id: 'S102', name: 'mustafa', present: 0, absent: 0 },
  { student_id: 'S103', name: 'aryan', present: 0, absent: 0 }
];

// Load face-api.js models
async function loadModels() {
  const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';
  await Promise.all([
    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
    faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
    faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
  ]);
  statusText.innerText = '✅ Models loaded, loading known faces...';
  await loadKnownFaces();
}

// Load known student faces
async function loadKnownFaces() {
  const labeledDescriptors = [];
  const images = ['atiksh.jpg', 'aryan.jpg', 'mustafa.jpg'];

  for (const image of images) {
    const label = image.split('.')[0];
    try {
      const img = await faceapi.fetchImage(`known_faces/${image}`);
      const detection = await faceapi.detectSingleFace(img, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor();
      if (detection) labeledDescriptors.push(
        new faceapi.LabeledFaceDescriptors(label, [detection.descriptor])
      );
    } catch(e) {
      console.error('Error loading face for ' + label, e);
    }
  }

  if(labeledDescriptors.length === 0){
    statusText.innerText = '❌ No known faces loaded!';
    return;
  }

  faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.7);
  statusText.innerText = '✅ Faces loaded, starting camera...';
  startVideo();
}

// Start webcam
function startVideo() {
  navigator.mediaDevices.getUserMedia({ video: {} })
    .then(stream => video.srcObject = stream)
    .catch(err => statusText.innerText = 'Camera access denied.');
}

// Main face detection loop
video.addEventListener('play', () => {
  const displaySize = { width: video.width, height: video.height };
  faceapi.matchDimensions(canvas, displaySize);

  setInterval(async () => {
    if(!faceMatcher) return;

    const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptors();
    
    const resized = faceapi.resizeResults(detections, displaySize);
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width,canvas.height);

    const now = new Date();

    resized.forEach(detection => {
      const bestMatch = faceMatcher.findBestMatch(detection.descriptor);
      new faceapi.draw.DrawBox(detection.detection.box, { label: bestMatch.toString() }).draw(canvas);

      if(bestMatch.label !== 'unknown' && !recognizedStudents.has(bestMatch.label)) {
        recognizedStudents.add(bestMatch.label);

        const student = students.find(s => s.name === bestMatch.label);
        if(student){
          // Mark attendance in local memory
          student.present++;

          statusText.innerText = `${bestMatch.label} is Present ✅`;

          // Send attendance to Flask backend
          fetch('/api/mark_present', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: student.student_id })
          })
          .then(res => res.json())
          .then(data => {
            console.log('Backend response:', data);
          })
          .catch(err => console.error('Error sending attendance:', err));

          // Optionally, send a snapshot to /api/face_login
          const snapshot = canvas.toDataURL('image/jpeg');
          fetch('/api/face_login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: snapshot })
          })
          .then(res => res.json())
          .then(data => console.log('Face login response:', data))
          .catch(err => console.error('Error sending face login:', err));
        }
      }
    });

  }, 1000);
});

loadModels();