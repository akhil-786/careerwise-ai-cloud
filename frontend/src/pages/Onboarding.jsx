import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createUser } from "../services/api";

function Onboarding() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    education: "",
    skills: "",
    interests: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await createUser({
        name: formData.name,
        email: formData.email,
        education: formData.education,
        skills: formData.skills
          .split(",")
          .map((skill) => skill.trim())
          .filter(Boolean),
        interests: formData.interests
          .split(",")
          .map((interest) => interest.trim())
          .filter(Boolean),
      });

      const userId = response.user.userId;

      localStorage.setItem("careercloud_userId", userId);

      navigate("/assessment");
    } catch (error) {
      console.error(error);
      setError("Unable to create your profile. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-container">
        <div className="onboarding-header">
          <div className="logo">
            Career<span>Cloud</span>
          </div>

          <div className="step-indicator">
            Step 1 of 3
          </div>
        </div>

        <div className="onboarding-card">
          <div className="form-intro">
            <span className="form-badge">Let's get started</span>

            <h1>Tell us about yourself</h1>

            <p>
              We'll use this information to personalize your
              career recommendations.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Full Name</label>

              <input
                type="text"
                name="name"
                placeholder="Enter your name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Email</label>

              <input
                type="email"
                name="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Education</label>

              <input
                type="text"
                name="education"
                placeholder="e.g. B.Tech CSE"
                value={formData.education}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Skills</label>

              <input
                type="text"
                name="skills"
                placeholder="Java, Python, DSA, AWS"
                value={formData.skills}
                onChange={handleChange}
              />

              <small>
                Separate multiple skills with commas.
              </small>
            </div>

            <div className="form-group">
              <label>Interests</label>

              <input
                type="text"
                name="interests"
                placeholder="Cloud, AI, Web Development"
                value={formData.interests}
                onChange={handleChange}
              />

              <small>
                Separate multiple interests with commas.
              </small>
            </div>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="primary-button submit-button"
              disabled={loading}
            >
              {loading
                ? "Creating Profile..."
                : "Continue to Assessment →"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Onboarding;