const UserService = require('../services/userService');
const Member = require('../models/member');
const bcrypt = require('bcryptjs');
const saltRounds = 10; // Number of salt rounds for bcrypt
const { spawn } = require('child_process');
const path = require('path');

exports.getUsers = async (req, res) => {
  try {
    const members = await Member.findAll();
    res.status(200).json(members);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.getUsersByID = async (req, res) => {
  try {
    const member = await Member.findByPk(req.params.id);
    if (member) {
      res.status(200).json(member);
    } else {
      res.status(404).json({ error: 'Member not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};



exports.createUser = async (req, res) => {
  try {
    const { username, password_hash, email, phone_number } = req.body;
    const newMember = await Member.create({
      username,
      password_hash,
      email,
      phone_number
    });
    res.status(201).json({ actionStatus: 'Success', message: 'Create Success!!', statusCode: 200, member: newMember });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

exports.updateUser = async (req, res) => {
  try {
    const { id } = req.params;
    const { username, password_hash, email, phone_number } = req.body;

    // Find the member by ID
    const member = await Member.findByPk(id);

    if (member) {
      // Update the member's details
      member.username = username || member.username;
      if (password_hash) {
        const hashedPassword = await bcrypt.hash(password_hash, saltRounds);
        member.password_hash = hashedPassword;
      }
      member.email = email || member.email;
      member.phone_number = phone_number || member.phone_number;
      member.updated_at = new Date(); // Update the timestamp

      // Save the updated member
      await member.save();

      res.status(200).json({ actionStatus: 'Success', message: 'Update Success!!', statusCode: 200, member: member });
    } else {
      res.status(404).json({ error: 'Member not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.deleteUser = async (req, res) => {
  try {
    const { id } = req.params;

    // Find the member by ID
    const member = await Member.findByPk(id);

    if (member) {
      // Delete the member
      await member.destroy();
      res.status(200).json({ actionStatus: 'Success', message: 'Delete Success!!', statusCode: 200 }); // 204 No Content
    } else {
      res.status(404).json({ error: 'Member not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

// API สำหรับเพิ่มใบหน้า
exports.addFace = async (req, res) => {
  try {
    const { id } = req.params;
    const member = await Member.findByPk(id);
    if (!member) return res.status(404).json({ error: 'Member not found' });

    const faceImage = req.file;
    if (!faceImage) return res.status(400).json({ error: 'Face image is required' });

    // เรียกใช้งาน Python script เพื่อตรวจจับและบันทึกใบหน้า
    const pythonScript = path.join(__dirname, '../services/face_recognition.py');
    const pythonProcess = spawn('python', [pythonScript , 'add', faceImage.path, member.member_id ]);

    pythonProcess.stdout.on('data', (data) => {
      console.log(`Output from Python: ${data}`);
      member.face_embedding = data.toString().trim(); // เก็บข้อมูลลงฐานข้อมูล
      member.save();
      res.status(200).json({ message: 'Face added successfully', member });
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Error from Python: ${data}`);
      res.status(500).json({ error: 'Error in face detection' });
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python process exited with code ${code}`);
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

// API สำหรับตรวจสอบใบหน้า
exports.checkFace = async (req, res) => {
  try {
    const { id } = req.params;
    const member = await Member.findByPk(id);
    if (!member) return res.status(404).json({ error: 'Member not found' });

    const faceImage = req.file;
    if (!faceImage) return res.status(400).json({ error: 'Face image is required' });

    // เรียกใช้งาน Python script เพื่อตรวจสอบใบหน้า
    if (member.face_embedding) {
      const pythonScript = path.join(__dirname, '../services/face_recognition.py');
      const pythonProcess = spawn('python', [pythonScript, 'check', faceImage.path, member.member_id]);
      pythonProcess.stdout.on('data', (data) => {
        console.log(`Output from Python: ${data}`);
        const result = data.toString().trim();
        if (result.includes('Face match found!')) {
          res.status(200).json({ message: result });
        } else {
          res.status(401).json({ message: result });
        }
      });

      pythonProcess.stderr.on('data', (data) => {
        console.error(`Error from Python: ${data}`);
        res.status(500).json({ error: 'Error in face comparison' });
      });

      pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
      });
    } else {
      res.status(500).json({ error: "No enroll" });
    }



  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};