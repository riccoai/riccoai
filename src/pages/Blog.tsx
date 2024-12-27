import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface BlogPost {
  id: number;
  attributes: {
    title: string;
    excerpt: string;
    publishedAt: string;
    readTime: string;
    content: string;
  }
}

const Blog = () => {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        setIsLoading(true);
        const response = await fetch('http://localhost:1337/api/posts', {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Fetched posts:', data);
        setPosts(data.data || []);
      } catch (error) {
        console.error('Error fetching posts:', error);
        setError('Failed to load blog posts');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPosts();
  }, []);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <h1 className="text-4xl font-bold mb-12">Blog</h1>
        <p className="text-gray-400">Loading posts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <h1 className="text-4xl font-bold mb-12">Blog</h1>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
      <h1 className="text-4xl font-bold mb-12">Blog</h1>
      {posts.length === 0 ? (
        <p className="text-gray-400">No posts found.</p>
      ) : (
        <div className="grid gap-8">
          {posts.map((post) => (
            <motion.article 
              key={post.id}
              className="bg-dark-lighter p-8 rounded-lg"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h2 className="text-2xl font-bold mb-4">{post.attributes.title}</h2>
              <div className="text-gray-400 mb-2">
                {new Date(post.attributes.publishedAt).toLocaleDateString()} • {post.attributes.readTime}
              </div>
              <p className="text-gray-300 mb-4">{post.attributes.excerpt}</p>
              <button className="text-primary hover:text-primary-dark transition-colors">
                Read More →
              </button>
            </motion.article>
          ))}
        </div>
      )}
    </div>
  );
};

export default Blog; 