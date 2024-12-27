const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

app.post('/contact', async (req, res) => {
  try {
    const { name, email, message } = req.body;
    // Process the contact form data
    // Send email, save to database, etc.
    
    res.json({ status: 'success' });
  } catch (error) {
    console.error('Error processing contact form:', error);
    res.status(500).json({ status: 'error', message: error.message });
  }
}); 