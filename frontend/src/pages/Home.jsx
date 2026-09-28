import { useNavigate } from "react-router-dom";

function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-page">
      <nav className="navbar">
        <div className="logo">
          Career<span>Cloud</span>
        </div>

        <button
          className="nav-button"
          onClick={() => navigate("/onboarding")}
        >
          Get Started
        </button>
      </nav>

      <main className="hero">
        <div className="hero-content">
          <div className="badge">
            AI-Powered Career Guidance
          </div>

          <h1>
            Discover the career
            <br />
            <span>that fits you.</span>
          </h1>

          <p>
            CareerCloud AI analyzes your skills, interests, and
            strengths to recommend suitable career paths and
            create a personalized learning roadmap.
          </p>

          <div className="hero-actions">
            <button
              className="primary-button"
              onClick={() => navigate("/onboarding")}
            >
              Start Career Assessment →
            </button>

            <button
              className="secondary-button"
              onClick={() => navigate("/onboarding")}
            >
              Explore How It Works
            </button>
          </div>

          <div className="features">
            <div>
              <strong>AI</strong>
              <span>Career Analysis</span>
            </div>

            <div>
              <strong>Personalized</strong>
              <span>Learning Roadmap</span>
            </div>

            <div>
              <strong>Cloud</strong>
              <span>Powered Platform</span>
            </div>
          </div>
        </div>

        <div className="hero-card">
          <div className="card-header">
            <span>Career Analysis</span>
            <span className="status">● AI Ready</span>
          </div>

          <div className="career-icon">✦</div>

          <h3>Your potential starts here.</h3>

          <p>
            Complete a short assessment and let AI identify
            career paths aligned with your strengths.
          </p>

          <div className="progress">
            <div className="progress-bar"></div>
          </div>

          <span className="progress-text">
            Personalized analysis
          </span>
        </div>
      </main>
    </div>
  );
}

export default Home;