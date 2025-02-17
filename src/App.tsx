import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { TypeAnimation } from 'react-type-animation';
import {
  Brain,
  Users,
  LineChart,
  Linkedin,
  Twitter,
  Instagram,
  Youtube,
  Menu,
  X,
  Glasses,
  Bot,
} from 'lucide-react';

import ServiceCard from './components/ServiceCard';
import MatrixEffect from './components/MatrixEffect';
import TestimonialCarousel from './components/TestimonialCarousel';
import BlogCard from './components/BlogCard';
import PrivacyPolicy from './components/PrivacyPolicy.tsx';
import ChatWidget from './components/ChatWidget';
import AnimatedStat from './components/AnimatedStat';
import Blog from './pages/Blog';
import NewsletterSignup from './components/NewsletterSignup';


interface ServiceDetails {
  features: string[];
  benefits: string[];
  idealFor: string;
  image: string;
}

interface Service {
  id: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  details: ServiceDetails;
}

interface BlogPost {
  id: number;
  attributes: {
    title: string;
    excerpt: string;
    date: string;
    readTime: string;
  }
}

interface NavigationItem {
  name: string;
  href: string;
}

interface ContactFormData {
  name: string;
  email: string;
  message: string;
}

const services: Service[] = [
  {
    id: "ai-tools",
    icon: <Brain className="w-8 h-8 text-primary" />,
    title: "AI Tools Integration",
    description: "Seamlessly integrate AI tools into your company or personal workflow for enhanced productivity and automation.",
    details: {
      features: [
        "Natural Language Processing for human-like interactions",
        "Integration with existing platforms",
        "Multi-language support",
        "24/7 availability"
      ],
      benefits: [
        "Improved response times",
        "Reduced workload",
        "Consistent experience",
        "Scalable solution"
      ],
      idealFor: "E-commerce, hospitality, professional services, and businesses looking to enhance customer interactions",
      image: "/images/service-1.jpg"
    }
  },
  {
    id: "ai-team",
    icon: <Users className="w-8 h-8 text-primary" />,
    title: "AI Agent Team Building",
    description: "Create powerful AI-powered teams to handle idea generation, data analysis and customer service efficiently.",
    details: {
      features: [
        "Customized AI agents for different functions",
        "Integration with existing systems",
        "Automated reporting",
        "Scalable architecture"
      ],
      benefits: [
        "Task automation",
        "Data-driven decisions",
        "Improved efficiency",
        "Complex process handling"
      ],
      idealFor: "Businesses looking to optimize operations and improve decision-making processes",
      image: "/images/service-2.jpg"
    }
  },
  {
    id: "analytics",
    icon: <LineChart className="w-8 h-8 text-primary" />,
    title: "Business Analytics",
    description: "Implement AI tools for marketing, information management, customer insights, and business analysis.",
    details: {
      features: [
        "Real-time data processing",
        "Predictive analytics",
        "Customer segmentation",
        "Customizable dashboards"
      ],
      benefits: [
        "Deep business insights",
        "Accurate forecasting",
        "Data-driven marketing",
        "Enhanced targeting"
      ],
      idealFor: "Businesses seeking to leverage data for strategic decision-making",
      image: "/images/service-3.jpg"
    }
  }
];

const navigation: NavigationItem[] = [
  { name: 'About', href: '#about' },
  { name: 'Services', href: '#services' },
  { name: 'Blog', href: '#blog' },
  { name: 'Contact', href: '#contact' }
];

const App: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMatrixActive, setIsMatrixActive] = useState(false);
  const [activeSection, setActiveSection] = useState('');
  const [areCardsExpanded, setAreCardsExpanded] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [notification, setNotification] = useState<{
    show: boolean;
    message: string;
    type: 'success' | 'error';
  }>({ show: false, message: '', type: 'success' });
  const [blogPosts, setBlogPosts] = useState<BlogPost[]>([]);

  useEffect(() => {
    const handleScroll = () => {
      const sections = document.querySelectorAll('section[id]');
      const scrollPosition = window.scrollY + 100;

      sections.forEach(section => {
        const sectionTop = (section as HTMLElement).offsetTop;
        const sectionHeight = (section as HTMLElement).offsetHeight;
        const sectionId = section.getAttribute('id') || '';

        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
          setActiveSection(sectionId);
        }
      });
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (notification.show) {
      const timer = setTimeout(() => {
        setNotification({ ...notification, show: false });
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [notification.show]);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const response = await fetch('http://localhost:1337/api/posts?populate=*');
        const data = await response.json();
        console.log('Fetched data:', data);
        setBlogPosts(data.data);
      } catch (error) {
        console.error('Error fetching blog posts:', error);
      }
    };

    fetchPosts();
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-dark">
        {/* Background Image */}
        <div 
          className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat opacity-10"
          style={{
            backgroundImage: "url('/images/background.jpg')"
          }}
        />

        <MatrixEffect isActive={isMatrixActive} />
        
        {/* Navigation */}
        <nav className="fixed w-full bg-dark-lighter/80 backdrop-blur-md z-50 border-b border-gray-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <Link to="/" className="h-8">
                  <img
                    src="/images/logo.png"
                    alt="ricco.AI"
                    className="h-full w-auto"
                  />
                </Link>
              </div>

              {/* Desktop Navigation */}
              <div className="hidden md:flex items-center space-x-4">
                {navigation.map((item) => (
                  <a
                    key={item.name}
                    href={item.href}
                    className={`nav-link ${activeSection === item.href.slice(1) ? 'active' : ''}`}
                  >
                    {item.name}
                  </a>
                ))}
              </div>

              <div className="flex items-center gap-4">
                <button
                  onClick={() => setIsMatrixActive(!isMatrixActive)}
                  className="text-primary hover:text-primary-dark transition-colors duration-300"
                  title="Toggle Matrix Mode"
                >
                  <Glasses className={`w-6 h-6 ${isMatrixActive ? 'text-primary' : 'text-primary/50'}`} />
                </button>

                <div className="md:hidden">
                  <button
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    className="text-gray-400 hover:text-white"
                  >
                    {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                  </button>
                </div>
              </div>
            </div>

            {/* Mobile Navigation */}
            <AnimatePresence>
              {isMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="md:hidden"
                >
                  <div className="px-2 pt-2 pb-3 space-y-1">
                    {navigation.map((item) => (
                      <a
                        key={item.name}
                        href={item.href}
                        className={`block px-3 py-2 rounded-md text-base font-medium ${
                          activeSection === item.href.slice(1)
                            ? 'text-white bg-primary/20'
                            : 'text-gray-300 hover:text-white hover:bg-primary/10'
                        }`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        {item.name}
                      </a>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={
            <>
              {/* Hero Section */}
              <section id="hero" className="min-h-[50vh] flex items-center justify-center relative z-10 pb-0 pt-32">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                  >
                    <h1 className="text-5xl md:text-7xl font-bold mb-6">
                      <TypeAnimation
                        sequence={[
                          'Transform Your Business',
                          2000,
                          'With AI Solutions',
                          2000,
                        ]}
                        wrapper="span"
                        speed={50}
                        repeat={Infinity}
                        className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400"
                      />
                    </h1>
                    <p className="text-xl md:text-2xl text-gray-400 mb-8">
                      Expert AI consulting to enhance your business productivity
                    </p>
                    <div className="flex justify-center gap-4">
                      <motion.button
                        onClick={() => setIsChatOpen(true)}
                        className="inline-block bg-primary hover:bg-primary-dark text-white font-semibold px-8 py-4 rounded-lg transition-colors duration-300 mb-32 flex items-center justify-center gap-2"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <Bot size={20} /> Chat with Us
                      </motion.button>
                      <motion.a
                        href="#contact"
                        className="inline-block bg-blue-500 hover:bg-blue-600 text-white font-semibold px-8 py-4 rounded-lg transition-colors duration-300 mb-32"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Meet with Us
                      </motion.a>
                    </div>
                  </motion.div>
                </div>
              </section>

              {/* Stats Bar */}
              <section className="py-4 relative z-10 bg-dark-lighter/50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <AnimatedStat end="95%" label="Efficiency Increase" />
                    <AnimatedStat end="24/7" label="AI-Powered Support" />
                    <AnimatedStat end="60%" label="Cost Reduction" />
                  </div>
                </div>
              </section>

              {/* About Section */}
              <section id="about" className="py-24 relative z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    <h2 className="section-title text-center hover-glow">About Us</h2>
                    <p className="section-subtitle text-center">
                      Empowering businesses with practical AI solutions that drive real results
                    </p>
                  </motion.div>

                  <div className="grid md:grid-cols-2 gap-12 items-center mt-12">
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6 }}
                    >
                      <h3 className="text-2xl font-bold mb-4">Your AI Automation Partner</h3>
                      <p className="text-gray-400 mb-6">
                        At Ricco.AI, we specialize in making artificial intelligence accessible and practical for businesses of all sizes. Our mission is to demystify AI technology and help you implement solutions that create real value for your organization.
                      </p>
                      <p className="text-gray-400">
                        With our expertise in AI integration, team building, and analytics, we've helped numerous businesses achieve their goals through intelligent automation and data-driven decision making.
                      </p>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, x: 20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6, delay: 0.2 }}
                    >
                      <TestimonialCarousel />
                    </motion.div>
                  </div>
                </div>
              </section>

              {/* Services Section */}
              <section id="services" className="py-24 bg-dark-lighter relative z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    <h2 className="section-title text-center hover-glow">Our Services</h2>
                    <p className="section-subtitle text-center">
                      Comprehensive AI solutions tailored to your business needs
                    </p>
                  </motion.div>

                  <div className="grid md:grid-cols-3 gap-8 mt-12">
                    {services.map((service) => (
                      <ServiceCard 
                        key={service.id}
                        {...service}
                        isExpanded={areCardsExpanded}
                        onExpand={setAreCardsExpanded}
                      />
                    ))}
                  </div>
                </div>
              </section>

              {/* Blog Section */}
              <section id="blog" className="py-24 relative z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    <h2 className="section-title text-center hover-glow">AI Insights</h2>
                    <p className="section-subtitle text-center">
                      Stay updated with the latest in AI technology and business applications
                    </p>
                  </motion.div>

                  <div className="grid md:grid-cols-3 gap-8 mt-12">
                    {blogPosts.slice(0, 3).map((post) => (
                      <BlogCard 
                        key={post.id}
                        title={post.attributes.title}
                        excerpt={post.attributes.excerpt}
                        date={post.attributes.publishedAt}
                        readTime={post.attributes.readTime}
                      />
                    ))}
                  </div>

                  <div className="text-center mt-12">
                    <Link 
                      to="/blog" 
                      className="inline-block bg-primary hover:bg-primary-dark text-white font-semibold px-8 py-4 rounded-lg transition-colors duration-300"
                    >
                      View All Posts
                    </Link>
                  </div>
                </div>
              </section>

              {/* Contact Section */}
              <section id="contact" className="py-24 bg-dark-lighter relative z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    <h2 className="section-title text-center hover-glow">Contact Us</h2>
                    <p className="section-subtitle text-center">
                      Ready to transform your business with AI? Let's talk.
                    </p>
                  </motion.div>

                  <div className="max-w-xl mx-auto mt-12">
                    <motion.form
                      className="space-y-6"
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6, delay: 0.2 }}
                      onSubmit={async (e: React.FormEvent<HTMLFormElement>) => {
                        e.preventDefault();
                        const form = e.currentTarget;
                        const formData = new FormData(form);
                        
                        const contactData: ContactFormData = {
                          name: formData.get('name') as string,
                          email: formData.get('email') as string,
                          message: formData.get('message') as string
                        };
                        
                        if (!contactData.name || !contactData.email || !contactData.message) {
                          setNotification({
                            show: true,
                            message: 'Please fill in all fields',
                            type: 'error'
                          });
                          return;
                        }

                        if (!contactData.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
                          setNotification({
                            show: true,
                            message: 'Please enter a valid email address',
                            type: 'error'
                          });
                          return;
                        }
                        
                        try {
                          const response = await fetch('http://localhost:8000/contact', {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(contactData)
                          });
                          
                          if (!response.ok) {
                            throw new Error('Network response was not ok');
                          }
                          
                          const data = await response.json();
                          
                          if (data.status === 'success') {
                            form.reset();
                            setNotification({
                              show: true,
                              message: 'Thank you for your message! We will get back to you soon.',
                              type: 'success'
                            });
                          } else {
                            throw new Error('Server returned error status');
                          }
                        } catch (error) {
                          console.error('Error:', error);
                          setNotification({
                            show: true,
                            message: 'Sorry, there was an error sending your message. Please try again.',
                            type: 'error'
                          });
                        }
                      }}
                    >
                      <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-300">
                          Name
                        </label>
                        <input
                          type="text"
                          id="name"
                          name="name"
                          className="mt-1 block w-full rounded-md bg-dark border-gray-600 text-white focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 px-4 py-3"
                        />
                      </div>
                      <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-300">
                          Email
                        </label>
                        <input
                          type="email"
                          id="email"
                          name="email"
                          className="mt-1 block w-full rounded-md bg-dark border-gray-600 text-white focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 px-4 py-3"
                        />
                      </div>
                      <div>
                        <label htmlFor="message" className="block text-sm font-medium text-gray-300">
                          Message
                        </label>
                        <textarea
                          id="message"
                          name="message"
                          rows={4}
                          className="mt-1 block w-full rounded-md bg-dark border-gray-600 text-white focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 px-4 py-3"
                        />
                      </div>
                      <motion.button
                        type="submit"
                        className="w-full bg-primary hover:bg-primary-dark text-white font-semibold px-6 py-3 rounded-lg transition-colors duration-300"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        Send Message
                      </motion.button>
                    </motion.form>
                  </div>
                </div>
              </section>
            </>
          } />
          <Route path="/blog" element={<Blog />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
        </Routes>

        {/* Footer */}
        <footer className="bg-dark py-12 relative z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <div className="mb-8 md:mb-0">
                <img src="/images/logo.png" alt="ricco.AI" className="h-8 w-auto" />
                <p className="text-gray-400 mt-2">Transforming businesses with AI solutions</p>
              </div>
              <div className="flex space-x-6">
                <a href="#" className="text-gray-400 hover:text-primary transition-colors duration-300">
                  <Linkedin className="w-6 h-6" />
                </a>
                <a href="#" className="text-gray-400 hover:text-primary transition-colors duration-300">
                  <Twitter className="w-6 h-6" />
                </a>
                <a href="#" className="text-gray-400 hover:text-primary transition-colors duration-300">
                  <Instagram className="w-6 h-6" />
                </a>
                <a href="#" className="text-gray-400 hover:text-primary transition-colors duration-300">
                  <Youtube className="w-6 h-6" />
                </a>
              </div>
            </div>
            <div className="mt-8 pt-8 border-t border-gray-800 text-center text-gray-400">
              <p className="mb-2">&copy; {new Date().getFullYear()} ricco.AI. All rights reserved.</p>
              <p>
                <Link to="/privacy" className="text-gray-400 hover:text-primary transition-colors duration-300">
                  Privacy Policy
                </Link>
              </p>
            </div>
          </div>
        </footer>
      </div>
      <ChatWidget isOpen={isChatOpen} setIsOpen={setIsChatOpen} />
      <AnimatePresence>
        {notification.show && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className={`fixed bottom-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
              notification.type === 'success' 
                ? 'bg-green-500' 
                : 'bg-red-500'
            } text-white`}
          >
            <p>{notification.message}</p>
            <button
              onClick={() => setNotification({ ...notification, show: false })}
              className="absolute top-1 right-1 text-white hover:text-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </BrowserRouter>
  );
}

export default App;