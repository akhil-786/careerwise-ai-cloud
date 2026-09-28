import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitAssessment } from "../services/api";

function Assessment() {
  const navigate = useNavigate();

  const [answers, setAnswers] = useState({
    programming: "",
    problemSolving: "",
    cloud: "",
    data: "",
    webDevelopment: "",
    interests: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setAnswers({
      ...answers,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const userId = localStorage.getItem("careercloud_userId");

    if (!userId) {
      setError("User information not found. Please complete onboarding again.");
      return;
    }

    setLoading(true);

    try {
      const response = await submitAssessment({
        userId,
        answers,
      });

      console.log("Assessment created:", response);

      const assessmentId = response.assessment.assessmentId;

        localStorage.setItem(
          "careercloud_assessmentId",
          assessmentId
        );

      navigate("/recommendation");
    } catch (err) {
      console.error(err);
      setError("Failed to submit assessment. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="assessment-page">
      <div className="assessment-card">
        <div className="assessment-header">
          <span className="eyebrow">Career Assessment</span>

          <h1>Let’s understand your interests.</h1>

          <p>
            Answer a few questions so CareerCloud AI can identify career
            directions that match your interests and skills.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="question">
            <label>How comfortable are you with programming?</label>

            <select
              name="programming"
              value={answers.programming}
              onChange={handleChange}
              required
            >
              <option value="">Select an option</option>
              <option value="Beginner">Beginner</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Advanced">Advanced</option>
            </select>
          </div>

          <div className="question">
            <label>How much do you enjoy problem solving?</label>

            <select
              name="problemSolving"
              value={answers.problemSolving}
              onChange={handleChange}
              required
            >
              <option value="">Select an option</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>

          <div className="question">
            <label>How interested are you in Cloud Computing?</label>

            <select
              name="cloud"
              value={answers.cloud}
              onChange={handleChange}
              required
            >
              <option value="">Select an option</option>
              <option value="Not interested">Not interested</option>
              <option value="Somewhat interested">Somewhat interested</option>
              <option value="Very interested">Very interested</option>
            </select>
          </div>

          <div className="question">
            <label>How interested are you in Data & AI?</label>

            <select
              name="data"
              value={answers.data}
              onChange={handleChange}
              required
            >
              <option value="">Select an option</option>
              <option value="Not interested">Not interested</option>
              <option value="Somewhat interested">Somewhat interested</option>
              <option value="Very interested">Very interested</option>
            </select>
          </div>

          <div className="question">
            <label>How interested are you in Web Development?</label>

            <select
              name="webDevelopment"
              value={answers.webDevelopment}
              onChange={handleChange}
              required
            >
              <option value="">Select an option</option>
              <option value="Not interested">Not interested</option>
              <option value="Somewhat interested">Somewhat interested</option>
              <option value="Very interested">Very interested</option>
            </select>
          </div>

          <div className="question">
            <label>What type of work interests you most?</label>

            <textarea
              name="interests"
              value={answers.interests}
              onChange={handleChange}
              placeholder="Example: building applications, solving problems, working with cloud, AI..."
              required
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? "Analyzing..." : "Submit Assessment →"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Assessment;