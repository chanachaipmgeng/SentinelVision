const Member = require('../models/member');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const secretKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZW1iZXJfaWQiOiJkZjE0OWM4Ni02Njc0LTRmODItYTE0Yi05OWFjNmZjYjJjNjIiLCJ1c2VybmFtZSI6ImNoYW5hY2hhaSIsImlhdCI6MTcyNDYzNDI0NSwiZXhwIjoxNzI0NjM3ODQ1fQ.bxa0LGelFhlGGb8PSgNd1oq-QZKqaNKbLA6oMuzEEeo'; // Replace with your own secret key
exports.login = async (req, res) => {
    try {
        const { username, password } = req.body;

        // Find the member by username
        const member = await Member.findOne({ where: { username } });

        if (!member) {
            return res.status(404).json({ error: 'Member not found' });
        }

        // Compare the password with the hashed password
        const isMatch = await bcrypt.compare(password, member.password_hash);

        if (!isMatch) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Generate a JWT
        const token = jwt.sign(
            { member_id: member.member_id, username: member.username },
            secretKey,
            { expiresIn: '1y' } // Token expires in 1 hour
        );

        res.status(200).json({ accessToken : token });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};