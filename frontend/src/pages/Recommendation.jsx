import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { generateRecommendation } from "../services/api";

function Recommendation() {
  const navigate = useNavigate();

  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const assessmentId = localStorage.getItem("careercloud_assessmentId");

    if (!assessmentId) {
      setError("Assessment information not found.");
      setLoading(false);
      return;
    }

    const generate = async () => {
      try {
        const response = await generateRecommendation(assessmentId);

        console.log("Recommendation response:", response);

        const data = response.recommendation;

        setRecommendation(data);

        if (data?.recommendationId) {
          localStorage.setItem(
            "careercloud_recommendationId",
            data.recommendationId
          );
        }
      } catch (err) {
        console.error(err);
        setError("Unable to generate your recommendation.");
      } finally {
        setLoading(false);
      }
    };

    generate();
  }, []);

  if (loading) {
    return (
      <div className="recommendation-page">
        <div className="recommendation-card loading-card">
          <div className="loader"></div>

          <h2>Analyzing your profile...</h2>

          <p>
            CareerCloud AI is analyzing your interests, skills and assessment
            responses.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendation-page">
        <div className="recommendation-card">
          <h2>Something went wrong</h2>

          <p className="form-error">{error}</p>

          <button onClick={() => navigate("/assessment")}>
            Back to Assessment
          </button>
        </div>
      </div>
    );
  }

  const text = recommendation?.recommendation || "";

  return (
    <div className="recommendation-page">
      <div className="recommendation-card">

        <span className="eyebrow">
          AI Career Recommendation
        </span>

        <h1>Your Career Direction</h1>

        <p className="intro">
          Based on your profile and assessment responses, CareerCloud AI has
          generated a personalized career direction for you.
        </p>

        <div className="career-result">
          <h2>Recommended Career</h2>

          <div className="career-title">
            Cloud Engineer / DevOps Engineer
          </div>
        </div>

        <div className="recommendation-section">
          <h2>Why This Matches You</h2>

          <p>
            Your strong interest in Cloud Computing, combined with your
            programming skills and problem-solving ability, makes cloud
            engineering and DevOps relevant career directions.
          </p>
        </div>

        <div className="recommendation-section">
          <h2>Your Current Strengths</h2>

          <ul>
            <li>High interest in Cloud Computing</li>
            <li>Foundational programming skills</li>
            <li>Good general problem-solving ability</li>
          </ul>
        </div>

        <div className="recommendation-section">
          <h2>Skill Gaps to Work On</h2>

          <ul>
            <li>AWS, Azure or GCP</li>
            <li>Infrastructure as Code</li>
            <li>Docker and Kubernetes</li>
            <li>CI/CD pipelines</li>
            <li>Cloud networking and security</li>
            <li>Monitoring and automation</li>
          </ul>
        </div>

        <div className="recommendation-section">
          <h2>AI-Generated Learning Direction</h2>

          <div className="ai-roadmap-preview">
            {text}
          </div>
        </div>

        <button
          onClick={() => navigate("/roadmap")}
          className="roadmap-button"
        >
          Generate My Learning Roadmap →
        </button>

      </div>
    </div>
  );
}

export default Recommendation;