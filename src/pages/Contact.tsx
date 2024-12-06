import React from 'react';

const handleSubmit = async (e: React.FormEvent) => {
    console.log('Form submission started');
    e.preventDefault();
    console.log('Default prevented');
    const formData = new FormData(e.target as HTMLFormElement);
    
    try {
        console.log('Sending to backend...');
        const response = await fetch('http://localhost:8000/contact', {
            method: 'POST',
            body: formData
        });
        
        console.log('Response received:', response);
        const data = await response.json();
        console.log('Data:', data);
        
        if (data.status === 'success') {
            // Clear the form
            (e.target as HTMLFormElement).reset();
            
            // Show success message
            alert('Thank you for your message! We will get back to you soon.');
        } else {
            alert('Sorry, there was an error sending your message. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Sorry, there was an error sending your message. Please try again.');
    }
}; 

const Contact = () => {
    return (
        <form onSubmit={handleSubmit}>
            <input 
                type="text" 
                name="name" 
                required 
                placeholder="Your Name"
            />
            <input 
                type="email" 
                name="email" 
                required 
                placeholder="Your Email"
            />
            <textarea 
                name="message" 
                required 
                placeholder="Your Message"
            ></textarea>
            <button type="submit">Send Message</button>
        </form>
    );
};

export default Contact; 