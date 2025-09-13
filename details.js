// Get the students data from localStorage
const students = JSON.parse(localStorage.getItem('studentsAttendance')) || [];
const tableBody = document.getElementById('attendanceTable');
const statusText=document.getElementById('');




// Create a row for each student
students.forEach(student => {
  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${student.name}</td>
    <td>${student.present || 0}</td>
    <td>${student.absent || 0}</td>
  `;
  tableBody.appendChild(row);
});

