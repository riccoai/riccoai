// Helper function to fetch posts from Strapi
export async function getPosts() {
  const response = await fetch('http://localhost:1337/api/posts?populate=*');
  const data = await response.json();
  return data.data;
} 