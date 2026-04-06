import { useState, useEffect, createContext, useContext, useRef } from 'react'
import './App.css'

const AuthContext = createContext();

function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token") || null);
  const [user, setUser] = useState(localStorage.getItem("username") || null);

  const login = (access_token, username) => {
    localStorage.setItem("token", access_token);
    localStorage.setItem("username", username);
    setToken(access_token);
    setUser(username);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function MainApp() {
  const { token, user, login, logout } = useContext(AuthContext);

  const [posts, setPosts] = useState([]);
  const [popularTags, setPopularTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [matchMode, setMatchMode] = useState('any');

  const [customTagInput, setCustomTagInput] = useState('');

  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  const [showCreatePost, setShowCreatePost] = useState(false);
  const [postTitle, setPostTitle] = useState('');
  const [postContent, setPostContent] = useState('');
  const [postTags, setPostTags] = useState([]);
  const [tagChipInput, setTagChipInput] = useState('');
  const [postError, setPostError] = useState('');
  const [postSuccess, setPostSuccess] = useState('');
  const tagInputRef = useRef(null);

  useEffect(() => {
    fetchPopularTags();
    fetchPosts();
  }, [selectedTags, matchMode]);

  const fetchPopularTags = async () => {
    try {
      const response = await fetch('http://localhost:8000/tags/popular');
      const data = await response.json();
      setPopularTags(data);
    } catch (error) {
      console.error('Error fetching tags', error);
    }
  };

  const fetchPosts = async () => {
    try {
      const tagsQuery = selectedTags.length > 0 ? `tags=${selectedTags.join(',')}` : '';
      const matchQuery = `match=${matchMode}`;
      const queryString = [tagsQuery, matchQuery].filter(Boolean).join('&');
      const url = `http://localhost:8000/posts?${queryString}`;
      const response = await fetch(url);
      const data = await response.json();
      setPosts(data);
    } catch (error) {
      console.error('Error fetching posts', error);
    }
  };

  const handleTagClick = (tag) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  const handleAddCustomTag = (e) => {
    e.preventDefault();
    const tag = customTagInput.trim().toLowerCase();
    if (tag && !selectedTags.includes(tag)) {
      setSelectedTags([...selectedTags, tag]);
    }
    setCustomTagInput('');
  };

  const handleMatchModeToggle = () => {
    setMatchMode(mode => mode === 'any' ? 'all' : 'any');
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      if (authMode === 'register') {
        const response = await fetch('http://localhost:8000/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, email, password })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        setAuthMode('login');
        setAuthError('Registration successful. Please log in.');
      } else {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        const response = await fetch('http://localhost:8000/auth/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        login(data.access_token, username);
        setShowAuth(false);
      }
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleTagChipKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTagChip();
    } else if (e.key === 'Backspace' && tagChipInput === '' && postTags.length > 0) {
      setPostTags(postTags.slice(0, -1));
    }
  };

  const addTagChip = () => {
    const tag = tagChipInput.trim().toLowerCase().replace(/,/g, '');
    if (tag && !postTags.includes(tag)) {
      setPostTags([...postTags, tag]);
    }
    setTagChipInput('');
  };

  const removeTagChip = (tag) => {
    setPostTags(postTags.filter(t => t !== tag));
  };

  const handleCreatePost = async (e) => {
    e.preventDefault();
    setPostError('');
    setPostSuccess('');
    if (!postTitle.trim()) return setPostError('Title is required.');
    if (!postContent.trim()) return setPostError('Content is required.');
    if (postTags.length === 0) return setPostError('Add at least one tag.');

    // Flush any tag still being typed
    const finalTags = tagChipInput.trim()
      ? [...new Set([...postTags, tagChipInput.trim().toLowerCase()])]
      : postTags;

    try {
      const response = await fetch('http://localhost:8000/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ title: postTitle, content: postContent, tags: finalTags })
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create post.');
      }
      setPostSuccess('Post created successfully!');
      setPostTitle(''); setPostContent(''); setPostTags([]); setTagChipInput('');
      fetchPosts(); fetchPopularTags();
      setTimeout(() => { setShowCreatePost(false); setPostSuccess(''); }, 1200);
    } catch (err) {
      if (err.message.includes('Token') || err.message.includes('401')) logout();
      setPostError(err.message);
    }
  };

  const openCreatePost = () => {
    setPostTitle(''); setPostContent(''); setPostTags([]);
    setTagChipInput(''); setPostError(''); setPostSuccess('');
    setShowCreatePost(true);
  };

  return (
    <div className="App">
      <header className="header">
        <div className="header-top">
          {user ? (
            <div className="auth-status">
              <span>Welcome, <strong>{user}</strong></span>
              <button className="auth-btn" onClick={logout}>Log Out</button>
            </div>
          ) : (
            <div className="auth-status">
              <button className="auth-btn" onClick={() => { setAuthMode('login'); setShowAuth(true); }}>Log In</button>
              <button className="auth-btn primary" onClick={() => { setAuthMode('register'); setShowAuth(true); }}>Sign Up</button>
            </div>
          )}
        </div>
        <h1>Tag-Based Content Discovery</h1>
        {user && (
          <button className="create-post-btn" onClick={openCreatePost}>+ Create Post</button>
        )}
      </header>

      {showAuth && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button className="close-modal" onClick={() => setShowAuth(false)}>&times;</button>
            <h2>{authMode === 'login' ? 'Log In' : 'Create Account'}</h2>
            {authError && <p className="auth-error">{authError}</p>}
            <form onSubmit={handleAuthSubmit} className="auth-form">
              <input type="text" placeholder="Username" required value={username} onChange={e => setUsername(e.target.value)} />
              {authMode === 'register' && (
                <input type="email" placeholder="Email address" required value={email} onChange={e => setEmail(e.target.value)} />
              )}
              <input type="password" placeholder="Password" required value={password} onChange={e => setPassword(e.target.value)} />
              <button type="submit" className="submit-btn">{authMode === 'login' ? 'Log In' : 'Sign Up'}</button>
            </form>
            <p className="auth-switch">
              {authMode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}>
                {authMode === 'login' ? 'Sign Up' : 'Log In'}
              </button>
            </p>
          </div>
        </div>
      )}

      {showCreatePost && (
        <div className="modal-overlay">
          <div className="modal-content modal-wide">
            <button className="close-modal" onClick={() => setShowCreatePost(false)}>&times;</button>
            <h2>Create a Post</h2>
            {postError && <p className="auth-error">{postError}</p>}
            {postSuccess && <p className="post-success">{postSuccess}</p>}
            <form onSubmit={handleCreatePost} className="auth-form">
              <input
                type="text"
                placeholder="Post title"
                value={postTitle}
                onChange={e => setPostTitle(e.target.value)}
                required
              />
              <textarea
                className="post-content-input"
                placeholder="Write your post content..."
                value={postContent}
                onChange={e => setPostContent(e.target.value)}
                rows={5}
                required
              />
              <div className="tag-chip-field" onClick={() => tagInputRef.current?.focus()}>
                {postTags.map(tag => (
                  <span key={tag} className="tag-chip">
                    #{tag}
                    <button type="button" className="tag-chip-remove" onClick={() => removeTagChip(tag)}>&times;</button>
                  </span>
                ))}
                <input
                  ref={tagInputRef}
                  type="text"
                  className="tag-chip-input"
                  placeholder={postTags.length === 0 ? 'Add tags (press Enter or comma)' : ''}
                  value={tagChipInput}
                  onChange={e => setTagChipInput(e.target.value)}
                  onKeyDown={handleTagChipKeyDown}
                  onBlur={addTagChip}
                />
              </div>
              <p className="tag-hint">Press <kbd>Enter</kbd> or <kbd>,</kbd> to add a tag. Press <kbd>Backspace</kbd> to remove the last tag.</p>
              <button type="submit" className="submit-btn">Publish Post</button>
            </form>
          </div>
        </div>
      )}

      <main className="main-content">
        <aside className="sidebar">
          <h3>Filter by Tags</h3>

          <form onSubmit={handleAddCustomTag} className="custom-tag-form">
            <input
              type="text"
              className="custom-tag-input"
              placeholder="Type a tag & press Enter…"
              value={customTagInput}
              onChange={e => setCustomTagInput(e.target.value)}
            />
            <button type="submit" className="custom-tag-add-btn" title="Add tag">+</button>
          </form>

          {selectedTags.length > 0 && (
            <div className="selected-tags-row">
              {selectedTags.map(tag => (
                <button
                  key={tag}
                  className="tag-button selected"
                  onClick={() => handleTagClick(tag)}
                >
                  {tag} <span className="tag-remove-x">×</span>
                </button>
              ))}
              <button className="clear-tags-btn" onClick={() => setSelectedTags([])}>Clear all</button>
            </div>
          )}

          <h4 className="popular-tags-label">Popular Tags</h4>
          <div className="tags-container">
            {popularTags.map(tagObj => (
              <button
                key={tagObj.tag}
                className={`tag-button ${selectedTags.includes(tagObj.tag) ? 'selected' : ''}`}
                onClick={() => handleTagClick(tagObj.tag)}
              >
                {tagObj.tag} <span className="tag-count">({tagObj.count})</span>
              </button>
            ))}
          </div>

          <div className="match-mode-toggle">
            <h4>Match Mode</h4>
            <label className="toggle-label">
              <input type="checkbox" checked={matchMode === 'all'} onChange={handleMatchModeToggle} />
              <span className="toggle-text">Require ALL selected tags ($all)</span>
            </label>
            <p className="mode-desc">
              Currently matching: <strong>{matchMode.toUpperCase()}</strong> selected tag(s)
            </p>
          </div>
        </aside>

        <section className="posts-section">
          <h2>Posts ({posts.length})</h2>
          {posts.length === 0 ? (
            <p className="no-posts">No posts match the selected tags.</p>
          ) : (
            <div className="posts-list">
              {posts.map(post => (
                <article key={post._id} className="post-card">
                  <h3>{post.title}</h3>
                  <p>{post.content}</p>
                  <div className="post-tags">
                    {post.tags?.map(t => (
                      <span
                        key={t}
                        className={`post-tag ${selectedTags.includes(t) ? 'post-tag-active' : ''}`}
                        onClick={() => handleTagClick(t)}
                        title="Click to filter"
                      >
                        {t}
                      </span>
                    ))}
                    {post.author && <span className="post-tag author-tag">by @{post.author}</span>}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App
